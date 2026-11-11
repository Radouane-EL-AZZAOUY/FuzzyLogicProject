# 4. Référence du moteur et du langage `fuzzyprolog`

## 4.1 Syntaxe

Sous-ensemble du Prolog standard, plus deux constructions.

| Élément | Exemple | Notes |
|---|---|---|
| Atome | `ali`, `'Route de rabat'`, `[]`, `!` | minuscule initiale ou entre apostrophes |
| Variable | `X`, `Nom`, `_`, `_Tmp` | `_` est anonyme (chaque occurrence est distincte) |
| Nombre | `3`, `2.5`, `1e3`, `-4` | entiers et flottants |
| Chaîne | `"Mohamed"` | type distinct des atomes (utilisé pour les données) |
| Terme composé | `date(1990, 5, 12)`, `f(X, g(Y))` | pas d'espace entre le foncteur et `(` |
| Liste | `[a, b, c]`, `[X \| T]`, `[]` | notation `.`/2 interne |
| Fait | `pere(ali, mohamed).` | degré 1 |
| Fait gradué | `aime(ali, foot) @ 0.8.` | degré dans `]0, 1]` |
| Règle | `p(X) :- q(X), r(X) @ 0.9.` | corps = conjonction ; `@` facultatif, en fin de clause |
| Similarité | `"casa" ~ "casablanca" @ 0.95.` | entre constantes seulement |
| Directive | `:- lambda_cut(0.3).` | voir 4.3 |
| Commentaires | `% ligne`, `/* bloc */` | |
| Fin de clause | `.` suivi d'un blanc ou de la fin | `=..` est un atome, pas une fin |

Opérateurs (priorité, type) : `:-` (1200 xfx/fx), `;` (1100 xfy), `->` (1050 xfy), `,` (1000 xfy),
`\+` (900 fy), `= \= == \== @< @> @=< @>= is =:= =\= < > =< >= ~` (700 xfx),
`+ -` (500 yfx), `* / // mod` (400 yfx), `** ^` (200), `- +` unaires (200 fy).

## 4.2 Sémantique des degrés

- Une solution a pour degré la **t-norme** de toutes les étapes de sa dérivation : degré de
  chaque clause utilisée, degré de chaque unification (similarités), degré de chaque prédéfini
  gradué.
- `T = min` (défaut), `product` ou `lukasiewicz` (`:- tnorm(product).`).
- `\+ G` vaut `1 − sup(deg G)` ; échoue si `G` est prouvé au degré 1. Le `sup` est calculé
  **sans** λ-coupure (une coupure est un élagage : elle ne doit jamais changer le degré d'une
  réponse survivante) ; la λ-coupure s'applique ensuite au résultat.
- Une dérivation dont le degré tombe sous `lambda_cut` est abandonnée (`:- lambda_cut(0.3).`).
- `findall/3` collecte les instances (copiées avec des variables fraîches) sans leur degré ;
  `with_degree/2` et `best_degree/2` exposent les degrés aux programmes.

## 4.3 Directives

| Directive | Effet |
|---|---|
| `:- lambda_cut(0.3).` | seuil λ de coupure des dérivations (défaut 0) |
| `:- tnorm(min).` | t-norme : `min`, `product`, `lukasiewicz` |
| `:- max_depth(500).` | nombre maximal d'étapes de résolution d'une dérivation (défaut 1000) |
| `:- occurs_check(false).` | désactive le test d'occurrence (défaut : activé, comme p. 56) |
| `:- transitive(false).` | similarité non fermée transitivement (défaut : fermeture max-min) |
| `:- similar(a, b, 0.8).` | équivalent de `a ~ b @ 0.8.` |

## 4.4 Prédicats de contrôle et prédéfinis

| Catégorie | Prédicats |
|---|---|
| Contrôle | `true`, `fail`, `false`, `!`, `,`, `;`, `->` (`(C -> T ; E)`), `\+`/`not`, `call/1..N`, `findall/3` |
| Unification / identité | `=`/2 (par similarité, gradué), `\=`/2, `==`/2, `\==`/2 |
| Ordre standard | `@<`, `@>`, `@=<`, `@>=`, `compare/3` (Var < Nombre < Atome < Chaîne < Structure) |
| Arithmétique | `is/2`, `=:=`, `=\=`, `<`, `>`, `=<`, `>=` ; `+ - * / // mod ** ^ abs min max sqrt float integer truncate round pi` |
| Types | `var`, `nonvar`, `atom`, `number`, `string`, `atomic`, `compound`, `is_list` |
| Texte | `string_lower/2`, `string_length/2`, `string_concat/3`, `atom_string/2` |
| Listes (prélude, cours p. 77) | `app/2`, `long/2`, `intersection/3`, `member/2`, `length/2`, `append/3`, `reverse/2`, `last/2`, `nth0/3`, `msort/2` |
| Flous | `similar/3` (degré déclaré), `text_similar/2` (Jaro-Winkler, gradué), `jaro_winkler/3`, `number_close/3` (gradué), `with_degree/2`, `best_degree/2` |
| Sortie | `write/1`, `writeln/1`, `nl/0` |

Un prédicat appelé mais non défini lève `ExecutionError` (« Prédicat inconnu »), ce qui détecte
les fautes de frappe au lieu d'échouer silencieusement.

## 4.5 Erreurs

| Exception | Cas |
|---|---|
| `ParseError` | syntaxe (avec ligne et colonne) |
| `ProgramError` | clause ou directive invalide, degré hors `]0,1]`, similarité entre non-constantes, fichier illisible |
| `ExecutionError` | prédicat inconnu, arithmétique invalide, division par zéro |
| `InstantiationError` | argument non instancié (`X is Y + 1`, `call(X)`) |
| `DepthLimitError` | dérivation plus longue que `max_depth` (récursion infinie probable) |

Toutes dérivent de `FuzzyPrologError`.

## 4.6 API Python

```python
from fuzzyprolog import Engine, program_from_text, register
from fuzzyprolog.builtins import graded

program = program_from_text('''
"casa" ~ "casablanca" @ 0.95.
habite(p1, "casablanca").
habite(p2, "casa").
meme_ville(A, B) :- habite(A, V), habite(B, V), A @< B.
''')

for solution in Engine(program).query("meme_ville(A, B)."):
    print(solution)            # A = p1, B = p2 (0.95)
    print(solution.explain())  # la dérivation, étape par étape

# Un prédéfini gradué fourni par l'application
MY_BUILTINS = {}

@register("proche/2", MY_BUILTINS)
def _proche(engine, args, subst, degree):
    x, y = (subst.walk(a).value for a in args)
    yield from graded(subst, 1 - abs(x - y) / 10)

engine = Engine(program, builtins=MY_BUILTINS)
```

Points d'entrée : `program_from_text`, `load_program(paths, prelude=True)`, `add_source`,
`Engine.query(text | goals, limit)`, `Engine.solve_all`, `Engine.best_degree`, `Engine.succeeds`,
`parse_query`, `parse_term`, `render`, `unify`.

## 4.7 CLI et REPL

```
fuzzyprolog [fichiers.pl …] [-q "but."]… [--max N] [--explain] [--lambda-cut λ] [--tnorm T]
            [--max-depth N] [--no-prelude]
```

Sans `-q`, une boucle interactive s'ouvre (`?- `) ; `halt.` la termine. Codes de retour : 0 ;
1 en cas d'erreur de chargement ou d'exécution (message sur la sortie d'erreur).

```
$ fuzzyprolog examples/humeur.pl -q "est_de_bonne_humeur(X)." --explain
?- est_de_bonne_humeur(X).
X = aicha (1.00)
est_de_bonne_humeur(X_3)  <-  clause l.7 : est_de_bonne_humeur(X) :- reussit_dans_le_travail(X), reussit_dans_sa_famille(X).
  reussit_dans_le_travail(aicha)  <-  clause l.15 : reussit_dans_le_travail(aicha).
  reussit_dans_sa_famille(aicha)  <-  clause l.16 : reussit_dans_sa_famille(aicha).
```

## 4.8 Limites

- Profondeur de dérivation bornée (1 000 étapes par défaut) : suffisante pour les règles
  métier et des listes de quelques centaines d'éléments ; `DepthLimitError` sinon.
- Pas d'`assert/retract`, de modules, d'exceptions Prolog, de `=..`, de `setof/bagof` ;
  pas d'entrées-sorties autres que `write`.
- Les chaînes et les atomes sont distincts : `"casa" \= casa`.
- La similarité porte sur les atomes et les chaînes, pas sur les foncteurs ; les nombres se
  comparent par valeur (`1 ~ 2` est refusé).
- Écarts à la norme ISO, assumés : `X = - 1` lit le nombre −1 ; `//` arrondit vers −∞ comme
  Python ; `1 == 1.0` réussit ; un atome quoté s'échappe en doublant l'apostrophe (`'it''s'`).
- Les substitutions sont copiées à chaque liaison et la trace est une liste chaînée : les
  dérivations de quelques milliers d'étapes restent rapides, au-delà le moteur n'est pas un
  interpréteur généraliste (ADR-002).
