"""
build_corpus.py — One-time offline script that extracts BPHS chapters
from Vol 1 OCR text, cleans them, chunks them into ~300-word passages,
appends hardcoded nakshatra notes, and writes corpus.json.

Run from the backend/ directory:
    python scripts/build_corpus.py

NOTE: The source djvu texts (data/BPHS - *.txt) are a copyrighted translation
and are git-ignored — they are NOT redistributed in this repo. The derived
corpus.json IS committed and is all the runtime/eval needs. To re-run this
build, obtain the BPHS Vol 1/2 (R. Santhanam) OCR text and place it in data/.
"""

import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (relative to backend/ working directory)
# ---------------------------------------------------------------------------
DATA_DIR = Path("data")
VOL1_PATH = DATA_DIR / "BPHS - 1 RSanthanam_djvu.txt"
OUT_PATH = Path("src/agent/knowledge/corpus.json")

# ---------------------------------------------------------------------------
# Chapters to extract from Vol 1
# ---------------------------------------------------------------------------
WANTED_CHAPTERS = {
    3:  "BPHS Ch.3 — Grahas",
    4:  "BPHS Ch.4 — Rashis",
    11: "BPHS Ch.11 — Bhava Significations",
    12: "BPHS Ch.12 — 1st House Effects",
    13: "BPHS Ch.13 — 2nd House Effects",
    14: "BPHS Ch.14 — 3rd House Effects",
    15: "BPHS Ch.15 — 4th House Effects",
    16: "BPHS Ch.16 — 5th House Effects",
    17: "BPHS Ch.17 — 6th House Effects",
    18: "BPHS Ch.18 — 7th House Effects",
    19: "BPHS Ch.19 — 8th House Effects",
    20: "BPHS Ch.20 — 9th House Effects",
    21: "BPHS Ch.21 — 10th House Effects",
    22: "BPHS Ch.22 — 11th House Effects",
    23: "BPHS Ch.23 — 12th House Effects",
}
END_CHAPTER = 24   # exclusive upper boundary

TARGET_WORDS = 300  # approximate chunk size in words

# ---------------------------------------------------------------------------
# Hardcoded nakshatra reference entries (verbatim — do not modify)
# ---------------------------------------------------------------------------
NAKSHATRA_NOTES = [
    {"text": "Ashwini (0°–13°20’ Aries) is ruled by Ketu and the Ashwini Kumaras, divine healers. It brings quick energy, healing ability, and an eager, pioneering spirit.", "source": "nakshatra-reference"},
    {"text": "Bharani (13°20’–26°40’ Aries) is ruled by Shukra and Yama, the god of death. It carries themes of birth, death, discipline, and holding what is difficult; people with Bharani prominent are fiercely loyal and intensely driven.", "source": "nakshatra-reference"},
    {"text": "Krittika (26°40’ Aries–10° Taurus) is ruled by Surya and the Pleiades. It is sharp, purifying, and critical — associated with fire, courage, and the capacity to cut through illusion.", "source": "nakshatra-reference"},
    {"text": "Rohini (10°–23°20’ Taurus) is ruled by Chandra and is said to be the Moon’s favourite nakshatra. It is fertile, sensual, and creative — associated with beauty, growth, and deep desire.", "source": "nakshatra-reference"},
    {"text": "Mrigashira (23°20’ Taurus–6°40’ Gemini) is ruled by Mangal and the deer’s head. It is curious, gentle, and ever-searching — bringing a restless, questing quality to those it influences.", "source": "nakshatra-reference"},
    {"text": "Ardra (6°40’–20° Gemini) is ruled by Rahu and the storm god Rudra. It brings intensity, emotional storms, and transformative breakthroughs — the nakshatra of destruction before renewal.", "source": "nakshatra-reference"},
    {"text": "Punarvasu (20° Gemini–3°20’ Cancer) is ruled by Guru and the goddess Aditi. It is the nakshatra of restoration and return — bringing renewal, optimism, and the ability to recover from setbacks.", "source": "nakshatra-reference"},
    {"text": "Pushya (3°20’–16°40’ Cancer) is ruled by Shani and Brihaspati. It is considered the most auspicious nakshatra — nourishing, supportive, and devoted to the wellbeing of others.", "source": "nakshatra-reference"},
    {"text": "Ashlesha (16°40’–30° Cancer) is ruled by Budha and the Nagas (serpents). It carries themes of penetrating insight, kundalini energy, and the capacity to see hidden truths — though it can also bring deception.", "source": "nakshatra-reference"},
    {"text": "Magha (0°–13°20’ Leo) is ruled by Ketu and the Pitrs (ancestral spirits). It is regal and ancestral — conferring leadership, pride in lineage, and a strong connection to tradition and heritage.", "source": "nakshatra-reference"},
    {"text": "Purva Phalguni (13°20’–26°40’ Leo) is ruled by Shukra and Bhaga, the god of delight. It is a nakshatra of rest, pleasure, and creative expression — associated with the arts, romance, and enjoying the fruits of one’s labour.", "source": "nakshatra-reference"},
    {"text": "Uttara Phalguni (26°40’ Leo–10° Virgo) is ruled by Surya and Aryaman. It brings partnership, social support, and disciplined effort — people of this nakshatra build enduring bonds and professional alliances.", "source": "nakshatra-reference"},
    {"text": "Hasta (10°–23°20’ Virgo) is ruled by Chandra and Savitar. It brings dexterity, craftsmanship, and practical intelligence — associated with healing hands, artisanship, and quick wit.", "source": "nakshatra-reference"},
    {"text": "Chitra (23°20’ Virgo–6°40’ Libra) is ruled by Mangal and Vishvakarma, divine architect. It is the nakshatra of brilliance and craftsmanship — associated with visual arts, jewellery, design, and an eye for beauty.", "source": "nakshatra-reference"},
    {"text": "Swati (6°40’–20° Libra) is ruled by Rahu and Vayu, the wind god. It brings independence, flexibility, and the capacity to scatter and spread — associated with trade, travel, and an adaptive social grace.", "source": "nakshatra-reference"},
    {"text": "Vishakha (20° Libra–3°20’ Scorpio) is ruled by Guru and the dual gods Indra-Agni. It is the nakshatra of focused purpose and determination — people with Vishakha prominent are persistent, ambitious, and willing to wait for their goals.", "source": "nakshatra-reference"},
    {"text": "Anuradha (3°20’–16°40’ Scorpio) is ruled by Shani and Mitra, god of friendship. It brings devotion, loyalty, and the ability to form deep bonds across distance — associated with friendships that transcend circumstance.", "source": "nakshatra-reference"},
    {"text": "Jyeshtha (16°40’–30° Scorpio) is ruled by Budha and Indra. It is the eldest — carrying themes of seniority, protection of the vulnerable, and the weight of responsibility; it can bring fame but also isolation.", "source": "nakshatra-reference"},
    {"text": "Mula (0°–13°20’ Sagittarius) is ruled by Ketu and Nirriti, goddess of dissolution. It is associated with uprooting, research into root causes, and the capacity to go to the very source — both destructive and deeply investigative.", "source": "nakshatra-reference"},
    {"text": "Purva Ashadha (13°20’–26°40’ Sagittarius) is ruled by Shukra and Apas, the water goddess. It brings invincibility, early victory, and purifying energy — associated with declarations, bold action, and idealism.", "source": "nakshatra-reference"},
    {"text": "Uttara Ashadha (26°40’ Sagittarius–10° Capricorn) is ruled by Surya and the Vishvadevas. It brings lasting victory, moral clarity, and the capacity to win through righteousness — patient and ultimately triumphant.", "source": "nakshatra-reference"},
    {"text": "Shravana (10°–23°20’ Capricorn) is ruled by Chandra and Vishnu. It is the nakshatra of listening, learning, and connection — associated with teachers, travellers, and those who spread wisdom across distances.", "source": "nakshatra-reference"},
    {"text": "Dhanishta (23°20’ Capricorn–6°40’ Aquarius) is ruled by Mangal and the eight Vasus. It brings wealth, music, and rhythm — associated with prosperity through disciplined effort and an ear for universal patterns.", "source": "nakshatra-reference"},
    {"text": "Shatabhisha (6°40’–20° Aquarius) is ruled by Rahu and Varuna, god of cosmic law. It is mysterious and solitary — associated with healing, astronomy, philosophy, and the keeping of deep secrets.", "source": "nakshatra-reference"},
    {"text": "Purva Bhadrapada (20° Aquarius–3°20’ Pisces) is ruled by Guru and Aja Ekapada. It brings intensity, asceticism, and a capacity for transformation through fire — people of this nakshatra can be spiritually fierce.", "source": "nakshatra-reference"},
    {"text": "Uttara Bhadrapada (3°20’–16°40’ Pisces) is ruled by Shani and Ahir Budhnya, the serpent of the deep. It brings depth, compassion, and wisdom — associated with rain, fertility, and the capacity to sustain others through difficulty.", "source": "nakshatra-reference"},
    {"text": "Revati (16°40’–30° Pisces) is ruled by Budha and Pushan, the nourisher. It is the final nakshatra — completing the zodiac cycle with themes of safe passage, abundance, and spiritual homecoming.", "source": "nakshatra-reference"},
]


# ---------------------------------------------------------------------------
# Sanskrit OCR garbage detection
# ---------------------------------------------------------------------------

def non_ascii_ratio(line: str) -> float:
    """Return the fraction of characters in *line* that are non-ASCII."""
    if not line:
        return 0.0
    non_ascii = sum(1 for c in line if ord(c) > 127)
    return non_ascii / len(line)


def _vowel_ratio_in_alpha(text: str) -> float:
    """
    Return the fraction of alphabetic characters that are vowels.
    Real English words have ~40% vowels.  Sanskrit transliteration
    consonant clusters (TT, jjj, ffjT, nsqffjT) are vowel-starved.
    """
    alpha = [c for c in text.lower() if c.isalpha()]
    if not alpha:
        return 0.0
    vowels = sum(1 for c in alpha if c in "aeiou")
    return vowels / len(alpha)


def _has_caret_or_pipe(line: str) -> bool:
    """True if line contains ^ or | characters (Sanskrit verse markers)."""
    return "^" in line or "|" in line


def _looks_like_english_token(tok: str) -> bool:
    """
    Heuristic: is this token likely an English word (not Sanskrit transliteration)?

    Positive signs: mostly lowercase, good vowel ratio, no internal ^ | digits.
    """
    # Strip surrounding punctuation
    clean = tok.strip(".,;:!?\"'()/\\[]{}|^*#@$%&~`<>+-=_0123456789")
    if len(clean) < 2:
        return False
    # Must contain only alpha characters (and optionally apostrophe/hyphen)
    alpha_chars = [c for c in clean if c.isalpha()]
    non_alpha = len(clean) - len(alpha_chars)
    # If ANY non-alpha character is inside the cleaned token, it's garbled.
    # (strip already removed outer punctuation; internal punctuation = noise)
    if non_alpha >= 1:
        return False
    if not alpha_chars:
        return False
    # Vowel check — Sanskrit clusters are consonant-heavy
    # Require at least 1 vowel for tokens with 3+ alpha chars
    vowels = sum(1 for c in clean.lower() if c in "aeiou")
    if vowels == 0 and len(alpha_chars) >= 3:
        return False
    # For tokens 4+ chars, require vowel ratio >= 15%
    if len(alpha_chars) >= 4 and vowels / len(alpha_chars) < 0.15:
        return False
    # Must be mostly lowercase (Sanskrit OCR has lots of uppercase clumps)
    upper = sum(1 for c in alpha_chars if c.isupper())
    if upper > len(alpha_chars) * 0.40:
        return False
    # Reject tokens starting with lowercase consonants followed by
    # immediately another consonant cluster — a strong Sanskrit marker
    # e.g. "fprounfofaiihi", "gw", "tnsqffjT", "twwwifa"
    if len(alpha_chars) >= 3:
        s = clean.lower()
        # gw, bk, fj, etc — 2-char tokens with no vowels already caught above
        # Catch 3+ char tokens starting with rare consonant pairs
        # (consonant pairs that basically never start English words)
        _rare_starts = re.compile(
            r'^(fp|fw|fT|fq|fj|gw|tw|bw|jq|kw|qf|mf|nf|pf|sr|sf|sq|'
            r'tTT|TTT|TTR|TNT|TN|TR|fn|fm|fd|fh|fv|fz|fx|fk|fl|fW|'
            r'fpr|fqr|fTO|fst|fsn|fsf|mft|nft|nfq|pnf|wnf)',
            re.IGNORECASE,
        )
        if _rare_starts.match(s):
            return False
    return True


def _long_consonant_cluster(text: str) -> bool:
    """True if text contains a run of 6+ consecutive consonants (a hallmark
    of Sanskrit OCR transliteration, essentially impossible in English).

    English has at most 4-5 consonants in a row (e.g. 'strengths' = ngths=5,
    'twelfths' = lfths=5). Six or more consecutive consonants do not occur
    in normal English prose.
    """
    # Exclude 'y' since it functions as a vowel in many English words
    consonants = re.compile(r'[bcdfghjklmnpqrstvwxzBCDFGHJKLMNPQRSTVWXZ]{6,}')
    return bool(consonants.search(text))


def is_garbage_line(line: str) -> bool:
    """
    Return True if the line is Sanskrit OCR noise or structural debris.

    Strategy: multiple fast heuristics; any match discards the line.
    Tuned to the specific OCR patterns in the BPHS Santhanam djvu files.
    """
    stripped = line.strip()
    if not stripped:
        return False

    # 1. High non-ASCII ratio (actual Devanagari / mojibake)
    if non_ascii_ratio(stripped) > 0.40:
        return True

    # 2. Standalone page numbers / very short numeric lines
    if re.match(r'^[\d\s]{1,6}$', stripped):
        return True

    # 3. Decorative separators
    if re.match(r'^[\-—_\.=*]{3,}$', stripped):
        return True

    # 4. Lines containing ^ or | combined with low English word count.
    #    Real English text in this book essentially never uses ^ or |.
    #    Verse markers look like: ||3||, Il3ll, i^|, )|?||, fait 11 ^ it
    if _has_caret_or_pipe(stripped):
        # Count genuinely English-looking tokens
        tokens = stripped.split()
        english_count = sum(1 for t in tokens if _looks_like_english_token(t))
        # If fewer than 70% of tokens look English, it's Sanskrit noise.
        # High threshold because ^ essentially never appears in real English.
        if english_count < len(tokens) * 0.70:
            return True

    # 4b. Lines starting with * or ** (Sanskrit verse markers)
    if stripped.startswith("*") and not stripped.startswith("**Note"):
        tokens = stripped.split()
        english_count = sum(1 for t in tokens if _looks_like_english_token(t))
        if english_count < len(tokens) * 0.50:
            return True

    # 5. Very low vowel ratio across the whole line — consonant-heavy clusters
    #    are the primary signature of Sanskrit transliteration.
    if _vowel_ratio_in_alpha(stripped) < 0.22 and len(stripped) >= 6:
        # But don't drop very short "real" lines like "I.", "A.", etc.
        alpha_total = sum(1 for c in stripped if c.isalpha())
        if alpha_total >= 5:
            return True

    # 6. Ends with Sanskrit verse-number markers like Il3ll, ||n||, )|?||
    #    These patterns close Sanskrit shlokas.
    if re.search(r'[Ii\|lL]{1,2}[\d\w\^*?]{1,4}[Ii\|lL]{1,2}\s*$', stripped):
        # Confirm it's not an English sentence ending (which wouldn't do this)
        if _vowel_ratio_in_alpha(stripped) < 0.30:
            return True

    # 7. Lines that are clearly just isolated Sanskrit transliteration tokens:
    #    single "word" with lots of uppercase and no vowels, or obviously
    #    OCR-transliterated (e.g. "tafcTrT:", "3TIVTT?", "3T^tTT^F7")
    tokens = stripped.split()
    if len(tokens) <= 3:
        alpha_chars = [c for c in stripped if c.isalpha()]
        if alpha_chars:
            upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            vowel_r = _vowel_ratio_in_alpha(stripped)
            if upper_ratio > 0.40 and vowel_r < 0.25:
                return True

    # 8. Lines containing a run of 4+ consecutive consonants anywhere.
    #    This pattern ("qrff", "srfffgt", "tnsqffjT") is a hallmark of
    #    Sanskrit transliteration OCR and essentially never occurs in English.
    if _long_consonant_cluster(stripped):
        # Make sure we're not discarding a line that has real English content too
        eng_tokens = sum(1 for t in stripped.split() if _looks_like_english_token(t))
        total_tokens = len(stripped.split())
        if eng_tokens < total_tokens * 0.60:
            return True

    # 9. Very short lines (2-4 tokens) where all tokens lack vowels or are
    #    single consonants — these are Sanskrit syllable fragments.
    if len(tokens) <= 4:
        all_bad = all(
            (not any(c in "aeiouAEIOU" for c in t) or
             sum(1 for c in t if c.isalpha()) <= 1)
            for t in tokens
            if t.strip(".,;:!?\"'()/\\[]{}|^*#@$%&~`<>+-=_0123456789")
        )
        alpha_present = any(c.isalpha() for c in stripped)
        if all_bad and alpha_present and len(stripped) >= 3:
            return True

    # 10. Single-word or very short lines that are only 1-4 lowercase letters.
    #     In this BPHS text, these are almost always Sanskrit shloka fragments
    #     (e.g. "i", "imi", "t") — never standalone English prose.
    if len(stripped) <= 5 and re.match(r'^[a-z]{1,5}$', stripped):
        return True

    # 11. Short lines (2-3 tokens, <= 25 chars) where fewer than half the tokens
    #     look like English — these are isolated Sanskrit syllable fragments.
    #     English sentences this short are always verse numbers or headings
    #     that start with a digit or capital (caught by other rules), so this
    #     is safe.
    if 2 <= len(tokens) <= 3 and len(stripped) <= 25:
        eng_count = sum(1 for t in tokens if _looks_like_english_token(t))
        if eng_count < len(tokens) * 0.60:
            return True

    return False


# ---------------------------------------------------------------------------
# Chapter boundary detection
# ---------------------------------------------------------------------------

def _parse_chapter_number(raw: str) -> int | None:
    """
    Parse a chapter number from the token(s) after 'Chapter ' or 'Chatter '.

    Handles:
    - Roman 'II' -> 11
    - OCR split '1 1' -> 11, '1 4' -> 14
    - Trailing page numbers: '12 129' -> 12
    - Trailing dots: '24.' -> 24
    """
    raw = raw.strip().rstrip('.')

    # Roman numeral 'II' -> chapter 11
    if re.match(r'^II$', raw, re.IGNORECASE):
        return 11

    parts = re.findall(r'\d+', raw)
    if not parts:
        return None
    if len(parts) == 1:
        return int(parts[0])

    first, second = parts[0], parts[1]
    # Single-digit + single-digit -> two-digit chapter number (OCR space)
    if len(first) == 1 and len(second) == 1:
        return int(first + second)
    # Otherwise, first is the chapter number (second is a page number)
    return int(first)


def find_chapter_boundaries(lines: list) -> dict:
    """
    Scan *lines* and return {chapter_number: first_line_index}.

    Rules:
    - A chapter header line must be a STANDALONE line containing ONLY
      'Chapter N' (digits/spaces/punctuation after 'Chapter', no prose).
    - Only the FIRST occurrence of each chapter number (by line order) is kept.
    - Checks the following patterns: 'Chapter N', 'Chatter N', 'Chapter II'.
    """
    # Pattern: the entire stripped line is "Chapter N" (no trailing prose)
    header_re = re.compile(
        r'^(Chapter|Chatter)\s+(?P<num>[\dI\s.]+)$',
        re.IGNORECASE,
    )

    boundaries = {}

    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        m = header_re.match(line)
        if not m:
            continue

        ch_num = _parse_chapter_number(m.group("num"))
        if ch_num is None:
            continue

        # Skip chapter numbers that are implausibly large (OCR artefacts)
        if ch_num > 100:
            continue

        if ch_num not in boundaries:
            boundaries[ch_num] = idx

    return boundaries


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def clean_lines(raw_lines: list) -> list:
    """
    Remove Sanskrit garbage and noise from a list of lines.
    Collapse consecutive blank lines to a single blank.
    Also removes page-header repetitions of 'Chapter N' and book title lines.
    """
    # Book title fragments and page headers that appear as running OCR artifacts
    _header_frags = re.compile(
        r'^('
        r'Brihat\s+Parasara'            # book title running header
        r'|Hora\s+Sastr'               # book title running header
        r'|Chapter\s+\d'               # repeated chapter headers
        r'|Chapter\s+II\s*$'           # "Chapter II" = roman numeral 11
        r'|Chatter\s+\d'              # OCR typo chapter headers
        r')',
        re.IGNORECASE,
    )

    # Very short OCR artifacts that appear as isolated page header fragments.
    # "Hi" is a common OCR artefact of a page number in this djvu scan.
    # Only match exact 2-3 char uppercase-start tokens that are standalone lines.
    _short_ocr_artifacts = re.compile(r'^(Hi|Hq|Hs)\s*$')

    cleaned = []
    prev_blank = False

    for line in raw_lines:
        stripped = line.rstrip()

        if not stripped:
            if not prev_blank:
                cleaned.append("")
            prev_blank = True
            continue

        if is_garbage_line(stripped):
            continue

        # Drop running page headers like "Brihat Parasara Hora Sastra",
        # repeated "Chapter N" headers mid-text, and short OCR artifacts
        s = stripped.strip()
        if _header_frags.match(s):
            continue
        if _short_ocr_artifacts.match(s):
            continue

        prev_blank = False
        cleaned.append(stripped.strip())

    # Strip leading/trailing blank lines from the block
    while cleaned and not cleaned[0]:
        cleaned.pop(0)
    while cleaned and not cleaned[-1]:
        cleaned.pop()

    return cleaned


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(lines: list, target_words: int = TARGET_WORDS) -> list:
    """
    Split *lines* into chunks of approximately *target_words* words.
    Breaks ONLY at paragraph boundaries (blank lines).  Never splits
    mid-paragraph.
    """
    # Group lines into paragraphs
    paragraphs = []
    current = []

    for line in lines:
        if not line.strip():
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            current.append(line.strip())

    if current:
        paragraphs.append(" ".join(current))

    # Accumulate paragraphs into chunks
    chunks = []
    current_words = []
    current_word_count = 0

    for para in paragraphs:
        words = para.split()
        if not words:
            continue

        current_words.extend(words)
        current_word_count += len(words)

        if current_word_count >= target_words:
            chunks.append(" ".join(current_words))
            current_words = []
            current_word_count = 0

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


# ---------------------------------------------------------------------------
# Chapter text extraction
# ---------------------------------------------------------------------------

def extract_chapter_text(lines: list, start_idx: int, end_idx: int) -> list:
    """
    Return lines[start_idx:end_idx], skipping the chapter header line and
    the chapter title line that immediately follows it.
    """
    block = lines[start_idx:end_idx]

    # Find and skip the opening "Chapter N" line
    skip_to = 0
    header_re = re.compile(r'^(Chapter|Chatter)\s+[\dI\s.]+$', re.IGNORECASE)

    for i, line in enumerate(block):
        if header_re.match(line.strip()):
            skip_to = i + 1
            break

    block = block[skip_to:]

    # Skip the title line (first non-blank line after the chapter header)
    new_start = 0
    for i, line in enumerate(block):
        if line.strip():
            new_start = i + 1
            break

    block = block[new_start:]

    return block


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_corpus() -> None:
    """Read BPHS Vol 1, extract chapters, clean, chunk, write corpus.json."""

    print(f"Reading {VOL1_PATH} ...")
    raw = VOL1_PATH.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()
    print(f"  {len(lines):,} lines loaded.")

    # Step 1: find chapter boundaries (first standalone header for each number)
    print("Finding chapter boundaries ...")
    boundaries = find_chapter_boundaries(lines)

    # Report what we found for the chapters we need
    needed = sorted(set(WANTED_CHAPTERS.keys()) | {END_CHAPTER})
    for ch in needed:
        if ch in boundaries:
            print(f"  Chapter {ch:2d} -> line {boundaries[ch] + 1}")
        else:
            print(f"  Chapter {ch:2d} -> NOT FOUND")

    corpus = []

    # Step 2: extract and process each wanted chapter
    sorted_wanted = sorted(WANTED_CHAPTERS.keys())

    for i, ch_num in enumerate(sorted_wanted):
        source_label = WANTED_CHAPTERS[ch_num]

        if ch_num not in boundaries:
            print(f"  WARNING: Chapter {ch_num} not found -- skipping.")
            continue

        start_idx = boundaries[ch_num]

        # End boundary: the NEXT chapter whose line index is AFTER start_idx.
        # We look through ALL known boundary chapters in document order,
        # not just the chapter-number order, to handle OCR ordering issues.
        #
        # Build a list of (line_idx, ch_number) for all chapters we recognise
        # as possible end markers (wanted chapters after this one + END_CHAPTER).
        possible_ends = []
        for ch_candidate, line_idx in boundaries.items():
            if line_idx > start_idx:
                possible_ends.append((line_idx, ch_candidate))

        # Sort by line position; take the smallest line index that is also
        # for a chapter number > ch_num (or == END_CHAPTER)
        # We must advance to the NEXT chapter in chapter-number sequence,
        # not just the next physical line.
        #
        # Strategy: any chapter whose NUMBER is >= ch_num+1 AND whose line
        # is the first after start_idx wins.
        valid_ends = [
            (line_idx, ch)
            for line_idx, ch in possible_ends
            if ch >= ch_num + 1
        ]
        valid_ends.sort()  # sort by line_idx ascending

        if valid_ends:
            end_idx = valid_ends[0][0]
        else:
            end_idx = len(lines)

        print(
            f"Processing Chapter {ch_num} "
            f"(lines {start_idx + 1} to {end_idx + 1}) ...",
            end=" ",
        )

        raw_block = extract_chapter_text(lines, start_idx, end_idx)
        cleaned = clean_lines(raw_block)
        chunks = chunk_text(cleaned)

        for chunk in chunks:
            corpus.append({"text": chunk, "source": source_label})

        print(f"{len(chunks)} chunks")

    # Step 3: append nakshatra notes
    corpus.extend(NAKSHATRA_NOTES)
    print(f"Appended {len(NAKSHATRA_NOTES)} nakshatra reference entries.")

    # Step 4: write corpus.json
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total = len(corpus)
    print(f"\nDone. Total entries written to {OUT_PATH}: {total}")

    # ---- Sample output ----
    def _first(source_substr: str) -> dict | None:
        for e in corpus:
            if source_substr in e["source"]:
                return e
        return None

    for label, substr in [
        ("Ch.3 (Grahas)", "Ch.3"),
        ("Ch.4 (Rashis)", "Ch.4"),
        ("Ch.11 (Bhava Significations)", "Ch.11"),
        ("Ch.12 (1st House)", "Ch.12"),
        ("Ch.23 (12th House)", "Ch.23"),
        ("nakshatra-reference", "nakshatra-reference"),
    ]:
        entry = _first(substr)
        print(f"\n--- Sample: {label} ---")
        if entry:
            # Print first 400 chars of text for readability
            preview = entry["text"][:400] + ("..." if len(entry["text"]) > 400 else "")
            print(f'  source: {entry["source"]}')
            print(f'  text:   {preview}')
        else:
            print("  (not found)")


if __name__ == "__main__":
    build_corpus()
