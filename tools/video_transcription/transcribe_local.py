import json
import os
import sys

import av
import numpy as np
from faster_whisper import WhisperModel


HEBREW_INITIAL_PROMPT = " ".join([
    "This audio is in Modern Hebrew.",
    "Transcribe in grammatically correct Modern Hebrew with natural punctuation.",
    "Prefer valid Hebrew words over phonetically similar invalid words.",
    "Preserve names, numbers, abbreviations, and technical terms.",
    "Do not translate, summarize, paraphrase, censor, or invent words.",
    "Use [לא ברור] for unintelligible words.",
])
LANGUAGE_CODES = {
    "arabic": "ar",
    "chinese": "zh",
    "english": "en",
    "french": "fr",
    "german": "de",
    "hebrew": "he",
    "hebreu": "he",
    "h\u00e9breu": "he",
    "hebraique": "he",
    "h\u00e9bra\u00efque": "he",
    "italian": "it",
    "portuguese": "pt",
    "spanish": "es",
}

ARABIC_REPLACEMENTS = {
    "اسبانيا": "إسبانيا",
    "اسرائيل": "إسرائيل",
    "اسرائيلي": "إسرائيلي",
    "الاسرائيلي": "الإسرائيلي",
    "الإسرائلي": "الإسرائيلي",
    "الاسرائيلية": "الإسرائيلية",
    "الاسرائيليين": "الإسرائيليين",
    "الشعب الفلسطني": "الشعب الفلسطيني",
    "الفلسطني": "الفلسطيني",
    "فلسطاني": "فلسطيني",
    "مسبوغ": "مسبوق",
    "مسبوخ": "مسبوق",
    "قامنية": "قانونية",
    "قامنونية": "قانونية",
    "تباطوها": "تواطؤها",
    "تباطؤها": "تواطؤها",
    "تواطئها": "تواطؤها",
    "العدول إسرائيل للدشعبنا": "العدو الإسرائيلي ضد شعبنا",
    "العدول إسرائيل": "العدو الإسرائيلي",
    "العدو إسرائيل": "العدو الإسرائيلي",
    "الدشعبنا": "ضد شعبنا",
    "متوارضة بالشدة": "متورطة بشدة",
    "متوارضة بشدة": "متورطة بشدة",
    "متورطة بالشدة": "متورطة بشدة",
    "الشدة في": "بشدة في",
    "كاف متوارضة": "كاف متورطة",
    "كاف متورطة بالشدة": "كاف متورطة بشدة",
    "الخطر الأحمر": "الخط الأحمر",
    "الخطر الأخضر": "الخط الأخضر",
    "الخد الأحمر": "الخط الأحمر",
    "الخد الأخضر": "الخط الأخضر",
    "الخطوط المستعمرات": "الخطوط المستعمرات",
    "تربب": "تربط",
    "تريب": "تربط",
    "فلسطانية": "فلسطينية",
    "فلسطانية مسلوبة": "فلسطينية مسلوبة",
    "التهجير القصري": "التهجير القسري",
    "التهجير القصرى": "التهجير القسري",
    "الأمام متحدة": "الأمم المتحدة",
    "الأمام المتحدة": "الأمم المتحدة",
    "الأمم متحدة": "الأمم المتحدة",
    "ما حدر": "ما حذر",
    "ما حدر منه": "ما حذر منه",
    "المجتمع المدن": "المجتمع المدني",
    "المجتمع المدنى": "المجتمع المدني",
    "محكمت العدد الدولية": "محكمة العدل الدولية",
    "محكمة العدد الدولية": "محكمة العدل الدولية",
    "محكمة العدل الدولي": "محكمة العدل الدولية",
    "الاحتلال العسكر": "الاحتلال العسكري",
    "الغدبية": "الغربية",
    "الغربيه": "الغربية",
    "وصحب الاستثمرات": "وسحب الاستثمارات",
    "وصحب الاستثمارات": "وسحب الاستثمارات",
    "وسحب الاستثماراة": "وسحب الاستثمارات",
    "فرض العقوبات BDS": "فرض العقوبات BDS",
    "بدأس": "BDS",
    "بي دي أس": "BDS",
    "بي دي اس": "BDS",
    "بي دي إس": "BDS",
    "ألستوم": "ألستوم",
    "الستوم": "ألستوم",
    "فيوليا": "فيوليا",
    "فويلية": "فيوليا",
    "فيولية": "فيوليا",
    "المشروع داته": "المشروع ذاته",
    "ذاته": "ذاته",
    "حمل عالمية": "حملة عالمية",
    "حملة عالمية لحركة المقاطع بدأس": "حملة عالمية لحركة المقاطعة BDS",
    "حركة المقاطع": "حركة المقاطعة",
    "إضربات": "إضرابات",
    "اضرابات": "إضرابات",
    "في في المصانع": "في المصانع",
    "دور مثل النروج": "دول مثل النرويج",
    "دور مثل النرويج": "دول مثل النرويج",
    "النروج": "النرويج",
    "ادارة": "إدارة",
    "واسعة الشركة": "وسعت الشركة",
    "وساعة الشركة": "وسعت الشركة",
    "إبادت شعبنا": "إبادة شعبنا",
    "إبادت شعبنا": "إبادة شعبنا",
    "مسائلة الشركات": "مساءلة الشركات",
    "مساءلة الشركات في اسبانيا": "مساءلة الشركات في إسبانيا",
    "البسكية": "الباسكية",
    "البسكيه": "الباسكية",
    "محمين دوليين": "محامين دوليين",
    "محامين دولين": "محامين دوليين",
    "ندرو أحرار": "ندعو أحرار",
    "ندرو احرار": "ندعو أحرار",
    "تصييد الحملة": "تصعيد الحملة",
    "تصعيد الحمله": "تصعيد الحملة",
    "التواطق": "التواطؤ",
    "التواطئ": "التواطؤ",
    "الأبرتايد الإسرائيل": "الأبرتايد الإسرائيلي",
    "الابرتايد": "الأبرتايد",
    "الأبارتايد": "الأبرتايد",
    "نظام الاستعمار الاستطاني": "نظام الاستعمار الاستيطاني",
    "الاستعمار الاستطاني": "الاستعمار الاستيطاني",
}

ARABIC_PHRASE_REPLACEMENTS = {
    "شركة تصنيع القطارات الباسكية كاف": "شركة تصنيع القطارات الباسكية CAF",
    "شركة كاف": "شركة CAF",
    "حركة المقاطعة BDS": "حركة المقاطعة BDS",
}


def normalize_language(language):
    if not language or language == "Auto detect":
        return None
    return LANGUAGE_CODES.get(language.lower(), language.lower()[:2])


def clean_text(text, language_code):
    if language_code != "ar":
        return text
    cleaned = text
    for wrong, right in ARABIC_REPLACEMENTS.items():
        cleaned = cleaned.replace(wrong, right)
    for wrong, right in ARABIC_PHRASE_REPLACEMENTS.items():
        cleaned = cleaned.replace(wrong, right)
    cleaned = " ".join(cleaned.split())
    return cleaned


def decode_audio_mono(media_file, sample_rate=16000):
    chunks = []
    with av.open(media_file) as container:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=sample_rate)
        for frame in container.decode(audio=0):
            for resampled in resampler.resample(frame):
                chunks.append(resampled.to_ndarray().reshape(-1))
        for resampled in resampler.resample(None):
            chunks.append(resampled.to_ndarray().reshape(-1))
    if not chunks:
        return np.zeros(0, dtype=np.float32), sample_rate
    audio = np.concatenate(chunks).astype(np.float32) / 32768.0
    return audio, sample_rate


def segment_features(audio, sample_rate, start, end):
    start_index = max(0, int(start * sample_rate))
    end_index = min(len(audio), int(end * sample_rate))
    clip = audio[start_index:end_index]
    if clip.size < sample_rate // 4:
        clip = audio[max(0, start_index - sample_rate // 4):min(len(audio), end_index + sample_rate // 4)]
    if clip.size == 0:
        return np.zeros(8, dtype=np.float32)

    rms = float(np.sqrt(np.mean(clip * clip) + 1e-12))
    zcr = float(np.mean(np.abs(np.diff(np.signbit(clip))))) if clip.size > 1 else 0.0
    sample_count = min(len(clip), sample_rate * 4)
    windowed = clip[:sample_count] * np.hanning(sample_count)
    spectrum = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(sample_count, 1.0 / sample_rate)
    total = float(spectrum.sum() + 1e-9)
    centroid = float((freqs * spectrum).sum() / total)
    cumulative = np.cumsum(spectrum)
    rolloff_index = min(len(freqs) - 1, int(np.searchsorted(cumulative, 0.85 * cumulative[-1])))
    rolloff = float(freqs[rolloff_index])
    bands = []
    for low, high in ((80, 180), (180, 300), (300, 600), (600, 1200)):
        mask = (freqs >= low) & (freqs < high)
        bands.append(float(spectrum[mask].sum() / total))
    return np.array([rms, zcr, centroid / 4000.0, rolloff / 8000.0, *bands], dtype=np.float32)


def kmeans_two(features):
    if len(features) < 2:
        return [0] * len(features)

    values = features.copy()
    values = (values - values.mean(axis=0)) / (values.std(axis=0) + 1e-6)
    energy_order = np.argsort(features[:, 0])
    centers = np.array([values[energy_order[0]], values[energy_order[-1]]])
    labels = np.zeros(len(values), dtype=int)

    for _ in range(30):
        distances = ((values[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        next_labels = distances.argmin(axis=1)
        if np.array_equal(labels, next_labels):
            break
        labels = next_labels
        for index in range(2):
            if np.any(labels == index):
                centers[index] = values[labels == index].mean(axis=0)
    return labels.tolist()


def smooth_labels(labels, segments):
    smoothed = labels[:]
    for index in range(1, len(smoothed) - 1):
        current = segments[index]
        previous = segments[index - 1]
        following = segments[index + 1]
        short_segment = current["end"] - current["start"] < 1.2
        close_to_neighbors = following["start"] - previous["end"] < 2.0
        if short_segment and close_to_neighbors and smoothed[index - 1] == smoothed[index + 1] != smoothed[index]:
            smoothed[index] = smoothed[index - 1]
    return smoothed


def add_speaker_labels(media_file, segments):
    if not segments:
        return segments
    audio, sample_rate = decode_audio_mono(media_file)
    if audio.size == 0:
        return segments

    features = np.vstack([
        segment_features(audio, sample_rate, segment["start"], segment["end"])
        for segment in segments
    ])
    labels = smooth_labels(kmeans_two(features), segments)

    label_names = {}
    next_label = 1
    for label in labels:
        if label not in label_names:
            label_names[label] = f"Speaker {next_label}"
            next_label += 1

    return [{**segment, "speaker": label_names[label]} for segment, label in zip(segments, labels)]

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) < 2:
        raise SystemExit("Usage: python transcribe_local.py <media-file> [language]")

    media_file = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "Auto detect"
    speed = sys.argv[3] if len(sys.argv) > 3 else "balanced"
    diarize = len(sys.argv) > 4 and sys.argv[4].lower() in ("true", "1", "yes", "diarize")
    language_code = normalize_language(language)
    if speed in ("fast", "balanced"):
        model_name = os.getenv("LOCAL_WHISPER_FAST_EN_MODEL" if language_code == "en" else "LOCAL_WHISPER_FAST_MODEL", "small")
    else:
        model_name = os.getenv("LOCAL_WHISPER_EN_MODEL" if language_code == "en" else "LOCAL_WHISPER_MODEL", "small")

    beam_size = 2 if speed == "fast" else 4 if speed == "balanced" else 5
    best_of = 2 if speed == "fast" else 4 if speed == "balanced" else 5
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    transcribe_options = {
        "vad_filter": True,
        "beam_size": beam_size,
        "best_of": best_of,
        "condition_on_previous_text": False,
        "task": "transcribe",
        "temperature": 0,
        "compression_ratio_threshold": 2.4,
        "log_prob_threshold": -1.0,
        "no_speech_threshold": 0.6,
    }
    if language_code:
        transcribe_options["language"] = language_code
    if language_code == "he":
        transcribe_options["initial_prompt"] = HEBREW_INITIAL_PROMPT

    segments, info = model.transcribe(media_file, **transcribe_options)
    detected_language = language_code or getattr(info, "language", None)
    normalized_segments = []
    full_text = []

    for segment in segments:
        text = clean_text(segment.text.strip(), detected_language)
        if not text:
            continue
        normalized_segments.append({
            "start": float(segment.start),
            "end": float(segment.end),
            "text": text,
        })
        full_text.append(text)

    if diarize:
        normalized_segments = add_speaker_labels(media_file, normalized_segments)

    print(json.dumps({
        "text": " ".join(full_text),
        "segments": normalized_segments,
        "provider": "local-whisper",
        "model": model_name,
        "language": detected_language or "auto",
        "diarized": diarize,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
