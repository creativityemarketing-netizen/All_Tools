<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('Expires: 0');

const DATA_FILE = __DIR__ . '/data/database.csv';

function respond(array $payload, int $status = 200): void {
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function numeric_id_to_shortcode(int $media_id): string {
    $alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
    $shortcode = '';
    while ($media_id > 0) {
        $shortcode = $alphabet[$media_id % 64] . $shortcode;
        $media_id = intdiv($media_id, 64);
    }
    return $shortcode;
}

function shortcode_to_numeric_id(string $shortcode): ?int {
    $alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
    $n = 0;
    $chars = str_split($shortcode);
    foreach ($chars as $char) {
        $idx = strpos($alphabet, $char);
        if ($idx === false) {
            return null;
        }
        $n = ($n * 64) + $idx;
    }
    return $n;
}

function extract_shortcode(string $value): ?string {
    $value = trim($value);
    if ($value === '' || in_array(strtolower($value), ['nan', 'none'], true)) {
        return null;
    }
    if (preg_match('~instagram\.com/(?:p|reels?|tv)/([A-Za-z0-9_-]+)~', $value, $matches)) {
        return $matches[1];
    }
    if (preg_match('/^\d+(?:_\d+)?$/', $value)) {
        return numeric_id_to_shortcode((int)explode('_', $value)[0]);
    }
    if (preg_match('/^[A-Za-z0-9_-]+$/', $value)) {
        return $value;
    }
    return null;
}

function extract_numeric_id(string $value): ?int {
    $value = trim($value);
    if ($value === '' || in_array(strtolower($value), ['nan', 'none'], true)) {
        return null;
    }
    $part = explode('_', $value)[0];
    if (preg_match('/^\d+$/', $part)) {
        return (int)$part;
    }
    return null;
}

function format_date_value(?string $raw): ?string {
    if ($raw === null || trim($raw) === '' || in_array(strtolower(trim($raw)), ['nan', 'none'], true)) {
        return $raw;
    }
    $value = trim($raw);
    $formats = [
        'Y-m-d\TH:i:s.u\Z',
        'Y-m-d\TH:i:s\Z',
        'Y-m-d H:i:s',
        'Y-m-d',
    ];
    foreach ($formats as $format) {
        $dt = DateTime::createFromFormat($format, $value, new DateTimeZone('UTC'));
        if ($dt instanceof DateTime) {
            return $dt->format('d F Y  -  H:i');
        }
    }
    try {
        $dt = new DateTime($value);
        return $dt->format('d F Y  -  H:i');
    } catch (Exception $e) {
        return $raw;
    }
}

function find_column(array $headers, array $candidates): ?string {
    $map = [];
    foreach ($headers as $header) {
        $map[strtolower(trim($header))] = $header;
    }
    foreach ($candidates as $candidate) {
        $key = strtolower($candidate);
        if (isset($map[$key])) {
            return $map[$key];
        }
    }
    return null;
}

function load_database(): array {
    static $cached = null;
    if ($cached !== null) {
        return $cached;
    }
    if (!is_readable(DATA_FILE)) {
        respond(['ok' => false, 'error' => 'Database file is missing.'], 500);
    }

    $handle = fopen(DATA_FILE, 'rb');
    if (!$handle) {
        respond(['ok' => false, 'error' => 'Cannot open database file.'], 500);
    }

    $headers = fgetcsv($handle);
    if (!$headers) {
        respond(['ok' => false, 'error' => 'Database is empty.'], 500);
    }

    $url_col = find_column($headers, ['Post URL', 'Link', 'URL']);
    $id_col = find_column($headers, ['Post ID', 'ID', 'Shortcode']);
    $date_col = find_column($headers, ['Published At', 'Publication Date', 'Date', 'published_at']);

    $index = [];
    $numeric = [];
    $rows = 0;

    while (($values = fgetcsv($handle)) !== false) {
        if (count($values) === 1 && trim((string)$values[0]) === '') {
            continue;
        }
        $row = [];
        foreach ($headers as $i => $header) {
            $row[$header] = $values[$i] ?? '';
        }
        $rows++;

        if ($date_col && isset($row[$date_col])) {
            $row['_date_formatted'] = format_date_value($row[$date_col]);
            $row['_date_raw'] = $row[$date_col];
        } else {
            $row['_date_formatted'] = null;
            $row['_date_raw'] = null;
        }

        $keys = [];
        $numeric_id = null;

        if ($url_col && !empty($row[$url_col])) {
            $sc = extract_shortcode((string)$row[$url_col]);
            if ($sc) {
                $keys[] = strtolower($sc);
                $row['_shortcode'] = $sc;
                $row['_url'] = 'https://www.instagram.com/p/' . $sc . '/';
            }
        }

        if ($id_col && !empty($row[$id_col])) {
            $raw_id = trim((string)$row[$id_col]);
            $sc = extract_shortcode($raw_id);
            if ($sc) {
                $keys[] = strtolower($sc);
                if (!isset($row['_shortcode'])) {
                    $row['_shortcode'] = $sc;
                    $row['_url'] = 'https://www.instagram.com/p/' . $sc . '/';
                }
            }
            $keys[] = strtolower($raw_id);
            $numeric_id = extract_numeric_id($raw_id);
            if ($numeric_id !== null) {
                $row['_numeric_id'] = (string)$numeric_id;
            }
        }

        foreach (array_unique($keys) as $key) {
            $index[$key] = $row;
        }
        if ($numeric_id !== null) {
            $numeric[] = [$numeric_id, $row];
        }
    }
    fclose($handle);

    usort($numeric, fn($a, $b) => $a[0] <=> $b[0]);

    $cached = [
        'index' => $index,
        'numeric' => $numeric,
        'info' => [
            'rows' => $rows,
            'indexed' => count($index),
            'columns' => $headers,
            'date_col' => $date_col,
            'url_col' => $url_col,
            'id_col' => $id_col,
        ],
    ];
    return $cached;
}

function search_exact(string $query, array $db): ?array {
    $sc = extract_shortcode($query);
    if ($sc && isset($db['index'][strtolower($sc)])) {
        return $db['index'][strtolower($sc)];
    }
    $key = strtolower(trim($query));
    return $db['index'][$key] ?? null;
}

function row_summary(int $numeric_id, array $row, string $direction): array {
    return [
        'numeric_id' => (string)$numeric_id,
        'post_id' => $row['Post ID'] ?? $row['id'] ?? (string)$numeric_id,
        'date_formatted' => $row['_date_formatted'] ?? $row['Published At'] ?? '-',
        'date_raw' => $row['_date_raw'] ?? '',
        'url' => $row['_url'] ?? $row['Post URL'] ?? '',
        'direction' => $direction,
    ];
}

function search_range(string $query, array $db, int $n = 1): ?array {
    $numeric = $db['numeric'];
    if (!$numeric) {
        return null;
    }

    $numeric_id = extract_numeric_id($query);
    if ($numeric_id === null) {
        $clean = preg_replace('/[^0-9]/', '', trim($query));
        if ($clean !== '') {
            $numeric_id = (int)$clean;
        }
    }
    if ($numeric_id === null) {
        return null;
    }

    $lo = 0;
    $hi = count($numeric);
    while ($lo < $hi) {
        $mid = intdiv($lo + $hi, 2);
        if ($numeric[$mid][0] < $numeric_id) {
            $lo = $mid + 1;
        } else {
            $hi = $mid;
        }
    }
    $pos = $lo;
    $below = array_slice($numeric, max(0, $pos - $n), $pos - max(0, $pos - $n));
    $above = array_slice($numeric, $pos, min(count($numeric), $pos + $n) - $pos);
    if (!$below && !$above) {
        return null;
    }

    $neighbors = [];
    foreach ($below as [$nid, $row]) {
        $neighbors[] = row_summary($nid, $row, 'before');
    }
    foreach ($above as [$nid, $row]) {
        $neighbors[] = row_summary($nid, $row, 'after');
    }

    $lower_date = $below ? ($below[count($below) - 1][1]['_date_formatted'] ?? null) : null;
    $upper_date = $above ? ($above[0][1]['_date_formatted'] ?? null) : null;
    if ($lower_date && $upper_date) {
        $range_label = 'Between ' . $lower_date . ' and ' . $upper_date;
    } elseif ($lower_date) {
        $range_label = 'After ' . $lower_date;
    } elseif ($upper_date) {
        $range_label = 'Before ' . $upper_date;
    } else {
        $range_label = 'Unknown';
    }

    $generated_sc = numeric_id_to_shortcode($numeric_id);
    return [
        'type' => 'range',
        'numeric_id' => (string)$numeric_id,
        'shortcode' => $generated_sc,
        'generated_url' => 'https://www.instagram.com/p/' . $generated_sc . '/',
        'range_label' => $range_label,
        'lower_date' => $lower_date,
        'upper_date' => $upper_date,
        'neighbors' => $neighbors,
        'total_in_db' => count($numeric),
    ];
}

$action = $_GET['action'] ?? '';
$db = load_database();

if ($action === 'stats') {
    respond(['ok' => true, 'info' => $db['info']]);
}

if ($action !== 'search') {
    respond(['ok' => false, 'error' => 'Unsupported action.'], 404);
}

$raw_input = file_get_contents('php://input') ?: '';
$decoded_input = $raw_input !== '' ? json_decode($raw_input, true) : [];
$input = is_array($decoded_input) ? $decoded_input : [];
$query = trim((string)($input['query'] ?? $_POST['query'] ?? $_GET['query'] ?? ''));
if ($query === '') {
    respond(['ok' => false, 'error' => 'Empty query.'], 400);
}

$exact = search_exact($query, $db);
if ($exact) {
    respond(['ok' => true, 'match' => 'exact', 'data' => $exact]);
}

if (preg_match('~instagram\.com/(?:p|reels?|tv)/([A-Za-z0-9_-]+)~', $query, $matches)) {
    $numeric_id = shortcode_to_numeric_id($matches[1]);
    if ($numeric_id !== null) {
        $range = search_range((string)$numeric_id, $db);
        if ($range) {
            respond(['ok' => true, 'match' => 'range', 'data' => $range]);
        }
    }
    respond(['ok' => false, 'error' => 'Post not found and no neighboring IDs could be estimated.'], 404);
}

$numeric_part = preg_replace('/[^0-9]/', '', explode('_', $query)[0]);
if ($numeric_part !== '' && strlen($numeric_part) !== 19) {
    respond([
        'ok' => false,
        'error' => 'Invalid Post ID - ' . strlen($numeric_part) . ' digits entered, Instagram Post IDs must be exactly 19 digits.',
        'hint' => 'Please check the ID and make sure no digit is missing or extra.',
    ], 400);
}

$range = search_range($query, $db);
if ($range) {
    respond(['ok' => true, 'match' => 'range', 'data' => $range]);
}

respond(['ok' => false, 'error' => 'Post not found and no neighboring IDs could be estimated.'], 404);
