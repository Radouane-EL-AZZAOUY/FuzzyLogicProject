# 6. Application d'irrigation `fuzzyirrigation`

## 6.1 Le problème

Dans un contexte de stress hydrique, l'irrigation « à heure fixe » gaspille l'eau : elle arrose un
sol déjà humide, la veille d'une pluie, ou insuffisamment par forte chaleur. Un agriculteur ou un
système domotique raisonne en termes vagues (« sol sec », « temps chaud », « air sec », « pluie
prévue ») et en règles d'expérience. C'est le cas d'école d'un **contrôleur flou** (Mamdani, 1975),
et un problème réel d'économie d'eau.

Cette application est volontairement compacte : elle prouve que le moteur est indépendant du
domaine (ADR-007) et que l'ajout d'une application tient dans une base de connaissances et trois
classes.

## 6.2 Variables

| Variable | Unité | Univers | Termes |
|---|---|---|---|
| `humidite_sol` | % | 0-100 | sec ↘ 20-35 · moyen △ 28-45-62 · humide ↗ 55-70 |
| `temperature` | °C | −5-50 | froide ↘ 10-18 · douce △ 14-23-32 · chaude ↗ 28-36 |
| `humidite_air` | % | 0-100 | faible ↘ 30-45 · moyenne △ 38-55-72 · elevee ↗ 65-80 |
| `pluie_prevue_mm` | mm / 24 h | 0-50 | nulle ↘ 1-4 · legere △ 2-7-13 · forte ↗ 10-18 |
| **`duree_arrosage`** (sortie) | min | 0-60 | nulle ⏢ 0-0-2-6 · courte △ 5-15-25 · moyenne △ 20-32-44 · longue ⏢ 38-50-60-60 |

## 6.3 Règles (`knowledge/irrigation.toml`, 13 règles)

```
I1  SI pluie_prevue_mm EST forte                                         ALORS duree_arrosage EST nulle
I2  SI pluie_prevue_mm EST legere ET humidite_sol N'EST PAS sec           ALORS duree_arrosage EST nulle
I3  SI pluie_prevue_mm EST legere ET humidite_sol EST sec                 ALORS duree_arrosage EST courte
I4  SI humidite_sol EST humide                                            ALORS duree_arrosage EST nulle
I5  SI humidite_sol EST moyen ET temperature EST chaude ET pluie_prevue_mm EST nulle ALORS duree_arrosage EST moyenne
I6  SI humidite_sol EST moyen ET temperature EST douce ET pluie_prevue_mm EST nulle  ALORS duree_arrosage EST courte
I7  SI humidite_sol EST moyen ET temperature EST froide                   ALORS duree_arrosage EST nulle      [0.8]
I8  SI humidite_sol EST moyen ET humidite_air EST faible ET temperature N'EST PAS froide ALORS duree_arrosage EST moyenne [0.7]
I9  SI humidite_sol EST sec ET temperature EST chaude ET pluie_prevue_mm EST nulle   ALORS duree_arrosage EST longue
I10 SI humidite_sol EST sec ET temperature EST douce ET pluie_prevue_mm EST nulle    ALORS duree_arrosage EST moyenne
I11 SI humidite_sol EST sec ET temperature EST froide ET pluie_prevue_mm EST nulle   ALORS duree_arrosage EST courte
I12 SI humidite_sol EST sec ET humidite_air EST faible ET pluie_prevue_mm EST nulle  ALORS duree_arrosage EST longue  [0.8]
I13 SI humidite_sol EST sec ET humidite_air EST elevee ET temperature N'EST PAS chaude ALORS duree_arrosage EST courte [0.6]
```

## 6.4 Domaine et service

- `SensorReading(humidite_sol, temperature, humidite_air, pluie_prevue_mm, plot)` : mesure validée
  (pourcentages dans `[0, 100]`, pluie non négative).
- `IrrigationDecision` : durée en minutes, libellé, `should_irrigate` (vrai si la durée dépasse le
  seuil de déclenchement de la pompe, 5 min par défaut), avertissements, trace complète.
- `IrrigationAdvisor` : charge la base (`from_file()`), `decide(reading)`, `decide_many(readings)`.

## 6.5 Utilisation

```bash
fuzzyirrigation decide --humidite-sol 18 --temperature 34 --humidite-air 28 --explain
# parcelle : arroser — 51 min (longue)
# Système « irrigation »
#   Entrées :
#     humidite_sol = 18  ->  sec=1.00, moyen=0.00, humide=0.00
#     ...
#   Règles déclenchées (2/13), par force :
#   - [I9] force=1.00 : SI humidite_sol EST sec ET temperature EST chaude ET pluie_prevue_mm EST nulle ALORS duree_arrosage EST longue
#   - [I12] force=0.80 : ...

fuzzyirrigation decide --humidite-sol 70 --temperature 22 --humidite-air 60 --json
fuzzyirrigation batch mesures.csv            # colonnes : parcelle, humidite_sol, temperature, humidite_air, pluie_prevue_mm
```

En Python :

```python
from fuzzyirrigation.advisor import IrrigationAdvisor
from fuzzyirrigation.domain import SensorReading

advisor = IrrigationAdvisor.from_file()
decision = advisor.decide(SensorReading(humidite_sol=25, temperature=31, humidite_air=35, pluie_prevue_mm=0))
print(decision.duration_minutes, decision.label, decision.should_irrigate)
```

## 6.6 Propriétés vérifiées par les tests

- Sol sec et chaleur ⇒ arrosage long ; sol humide ou pluie forte prévue ⇒ pas d'arrosage.
- La durée décroît avec l'humidité du sol (monotonie).
- Validation des mesures, CLI (décision unitaire, JSON, lot CSV, code de retour 1 en cas d'erreur).
