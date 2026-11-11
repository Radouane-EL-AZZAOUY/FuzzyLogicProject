"""Synthetic dataset generator with ground truth (names and persons are fictitious).

Duplicates are produced by realistic perturbations: transliteration variants of
Arabic names, typos, year-only or swapped dates, city aliases, phone formatting,
missing fields. *Hard negatives* (namesakes with different birth dates) are added
to measure precision. Fully reproducible for a given seed.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path

FIRST_NAMES: dict[str, list[str]] = {
    "Mohamed": ["Mohammed", "Muhammad", "Mohamad", "M'hamed"],
    "Youssef": ["Yousef", "Yusuf", "Youssof"],
    "Yassine": ["Yacine", "Yassin"],
    "Hicham": ["Hisham", "Hichame"],
    "Rachid": ["Rashid", "Rachide"],
    "Abdellah": ["Abdallah", "Abd Allah", "Abdullah"],
    "Abdelkader": ["Abdelkadir", "Abd El Kader"],
    "Omar": ["Umar", "Omar"],
    "Hamza": ["Hamzah"],
    "Ayoub": ["Ayyoub", "Ayub"],
    "Amine": ["Amin", "Amyne"],
    "Mehdi": ["Mahdi", "El Mehdi"],
    "Ilyas": ["Ilias", "Elias"],
    "Said": ["Saïd", "Sa'id"],
    "Hassan": ["Hasan", "Hassane"],
    "Fatima Zahra": ["Fatima-Zohra", "Fatima Ezzahra", "Fatimazahra", "Fatima Zohra"],
    "Khadija": ["Khadidja", "Khadijah"],
    "Zineb": ["Zaynab", "Zeineb", "Zineb"],
    "Soukaina": ["Sukaina", "Soukayna"],
    "Meryem": ["Mariam", "Maryam", "Meriem"],
    "Nour": ["Nor", "Noor"],
    "Imane": ["Iman", "Imen"],
    "Salma": ["Selma"],
    "Houda": ["Huda", "Hoda"],
    "Oumaima": ["Oumayma", "Umaima"],
    "Sara": ["Sarah"],
    "Aya": ["Aya"],
    "Ikram": ["Ikrame"],
    "Siham": ["Sihame", "Sihem"],
    "Nadia": ["Nadya"],
}
LAST_NAMES: dict[str, list[str]] = {
    "El Amrani": ["Lamrani", "El-Amrani", "Elamrani", "Al Amrani"],
    "Benjelloun": ["Ben Jelloun", "Benjellon"],
    "Ouazzani": ["Wazzani", "El Ouazzani"],
    "Chraibi": ["Chraïbi", "Shraibi"],
    "El Fassi": ["Fassi", "Alfassi", "El Fasi"],
    "Bennani": ["Benani", "Bennany"],
    "Tazi": ["Tazy"],
    "Lahlou": ["Lahlo", "Lahlou"],
    "Berrada": ["Barrada", "Berada"],
    "Kabbaj": ["Kabaj", "Kabbadj"],
    "Alaoui": ["Alaui", "El Alaoui", "Alawi"],
    "Sefrioui": ["Sefriui", "Sefrioui"],
    "Mansouri": ["El Mansouri", "Mansoury"],
    "Zerouali": ["Zeroual", "Zerwali"],
    "Haddad": ["Hadad"],
    "Saidi": ["Saïdi", "Essaidi"],
    "Bakkali": ["Bakali", "El Bakkali"],
    "Cherkaoui": ["Cherkaui", "Charkaoui"],
    "Idrissi": ["Idrisi", "El Idrissi", "Drissi"],
    "Hajji": ["Haji", "El Hajji"],
    "Kettani": ["Ketani", "El Kettani"],
    "Boukhari": ["Bokhari", "Boukhary"],
    "Ait Ali": ["Aitali", "Ait-Ali"],
    "Ould Said": ["Ouldsaid", "Ould-Said"],
    "Ziani": ["Zyani"],
    "Naciri": ["Nasiri", "Naceri"],
    "Belkadi": ["Belkadi", "Bel Kadi"],
    "Rhazi": ["Ghazi", "Razi"],
    "Tahiri": ["Tahiri", "Tahri"],
    "Skalli": ["Sqalli", "Skali"],
}
CITIES: dict[str, list[str]] = {
    "Casablanca": ["Casa", "Dar El Beida"],
    "Rabat": [],
    "Mohammedia": ["Fedala"],
    "Fes": ["Fez"],
    "Marrakech": ["Marrakesh"],
    "Tanger": ["Tangier", "Tanja"],
    "Agadir": [],
    "Meknes": ["Meknas"],
    "Oujda": ["Oujda Angad"],
    "Kenitra": [],
    "Tetouan": [],
    "El Jadida": ["Mazagan"],
    "Laayoune": ["El Aaiun"],
    "Essaouira": ["Mogador"],
}
RECORDS_FILE = "personnes_exemple.csv"
TRUTH_FILE = "verite_exemple.csv"
COLUMNS = ("id", "nom", "prenom", "date_naissance", "ville", "telephone", "email", "source")


@dataclass
class _Person:
    person_id: str
    first: str
    last: str
    year: int
    month: int
    day: int
    city: str
    phone: str
    email: str


def _variant(rng: random.Random, canonical: str, table: dict[str, list[str]]) -> str:
    options = table.get(canonical, [])
    return rng.choice(options) if options and rng.random() < 0.8 else _typo(rng, canonical)


def _typo(rng: random.Random, text: str) -> str:
    letters = list(text)
    if len(letters) < 4:
        return text
    i = rng.randrange(1, len(letters) - 1)
    kind = rng.random()
    if kind < 0.4:  # swap
        letters[i], letters[i + 1] = letters[i + 1], letters[i]
    elif kind < 0.7:  # drop
        del letters[i]
    else:  # double
        letters.insert(i, letters[i])
    return "".join(letters)


def _format_phone(rng: random.Random, phone: str) -> str:
    kind = rng.random()
    if kind < 0.3:
        return "+212 " + phone[1:2] + " " + " ".join(phone[i : i + 2] for i in range(2, 10, 2))
    if kind < 0.5:
        return "00212" + phone[1:]
    if kind < 0.7:
        return phone[:2] + "-" + "-".join(phone[i : i + 2] for i in range(2, 10, 2))
    return phone


def _date_text(year: int, month: int, day: int) -> str:
    return f"{year:04d}-{month:02d}-{day:02d}"


def _perturb_date(rng: random.Random, p: _Person) -> str:
    kind = rng.random()
    if kind < 0.15:
        return str(p.year)  # year only
    if kind < 0.25 and p.day <= 12:
        return _date_text(p.year, p.day, p.month)  # day/month swapped
    if kind < 0.35:
        return _date_text(p.year, p.month, max(1, min(28, p.day + rng.choice((-2, -1, 1, 2)))))
    if kind < 0.42:
        return ""  # unknown
    if kind < 0.47:
        return _date_text(p.year + rng.choice((-1, 1)), p.month, p.day)
    return _date_text(p.year, p.month, p.day)


def _base_row(rng: random.Random, p: _Person, source: str) -> dict[str, str]:
    return {
        "nom": p.last,
        "prenom": p.first,
        "date_naissance": _date_text(p.year, p.month, p.day),
        "ville": p.city,
        "telephone": p.phone,
        "email": p.email if rng.random() < 0.6 else "",
        "source": source,
    }


def _duplicate_row(rng: random.Random, p: _Person, source: str) -> dict[str, str]:
    last = _variant(rng, p.last, LAST_NAMES) if rng.random() < 0.6 else p.last
    first = _variant(rng, p.first, FIRST_NAMES) if rng.random() < 0.6 else p.first
    aliases = CITIES.get(p.city, [])
    city_roll = rng.random()
    city = (
        rng.choice(aliases)
        if aliases and city_roll < 0.25
        else ("" if city_roll < 0.35 else p.city)
    )
    phone_roll = rng.random()
    phone = "" if phone_roll < 0.3 else _format_phone(rng, p.phone)
    return {
        "nom": last,
        "prenom": first,
        "date_naissance": _perturb_date(rng, p),
        "ville": city,
        "telephone": phone,
        "email": p.email if rng.random() < 0.3 else "",
        "source": source,
    }


def generate_dataset(out_dir: Path, persons: int = 150, seed: int = 7) -> tuple[Path, Path, int]:
    rng = random.Random(seed)
    firsts, lasts, cities = list(FIRST_NAMES), list(LAST_NAMES), list(CITIES)
    people: list[_Person] = []
    for index in range(persons):
        first, last = rng.choice(firsts), rng.choice(lasts)
        year = rng.randint(1950, 2006)
        month, day = rng.randint(1, 12), rng.randint(1, 28)
        city = rng.choice(cities)
        phone = "0" + rng.choice("67") + "".join(rng.choice("0123456789") for _ in range(8))
        local = f"{first.split()[0].lower()}.{last.replace(' ', '').lower()}"
        email = f"{local}{rng.randint(1, 99)}@exemple.ma"
        people.append(
            _Person(f"PERS{index + 1:04d}", first, last, year, month, day, city, phone, email)
        )
    # hard negatives: namesakes of existing persons with other dates / cities / phones
    namesakes = max(1, persons // 12)
    for index in range(namesakes):
        model = rng.choice(people[:persons])
        year = rng.randint(1950, 2006)
        while year == model.year:
            year = rng.randint(1950, 2006)
        phone = "0" + rng.choice("67") + "".join(rng.choice("0123456789") for _ in range(8))
        people.append(
            _Person(
                f"PERS{persons + index + 1:04d}",
                model.first,
                model.last,
                year,
                rng.randint(1, 12),
                rng.randint(1, 28),
                rng.choice(cities),
                phone,
                f"homonyme{index}@exemple.ma",
            )
        )
    sources = ["inscriptions", "sante", "clients"]
    rows: list[tuple[dict[str, str], str]] = []
    for p in people:
        rows.append((_base_row(rng, p, sources[0]), p.person_id))
        extra = 0 if rng.random() < 0.45 else (1 if rng.random() < 0.7 else 2)
        for k in range(extra):
            rows.append((_duplicate_row(rng, p, sources[1 + k]), p.person_id))
    rng.shuffle(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    records_path, truth_path = out_dir / RECORDS_FILE, out_dir / TRUTH_FILE
    with (
        records_path.open("w", encoding="utf-8", newline="") as handle,
        truth_path.open("w", encoding="utf-8", newline="") as truth_handle,
    ):
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        truth_writer = csv.writer(truth_handle)
        truth_writer.writerow(["id", "personne"])
        for number, (row, person_id) in enumerate(rows, start=1):
            identifier = f"p{number:04d}"
            writer.writerow({"id": identifier, **row})
            truth_writer.writerow([identifier, person_id])
    return records_path, truth_path, len(rows)
