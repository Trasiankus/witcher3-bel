# witcher3-bel — Беларуская лакалізацыя «The Witcher 3: Wild Hunt»

Belarusian localization of *The Witcher 3: Wild Hunt* (Game of the
Year / Next-Gen v4.04). Зроблена з дапамогай [Crowdin](https://crowdin.com/)`.w3strings`.

Далучыцца да праекту можна тут: https://crowdin.com/project/witcher-3-bel

## Стан перакладу

| Частка | Перакладзена | Усяго | Адсотак |
|---|---:|---:|---:|
| Базавая гульня | 50 241 | 69 683 | **72.1 %** |
| Hearts of Stone | 0 | 6 606 | 0 % |
| Blood and Wine | 0 | 17 157 | 0 % |
| Іншыя DLC | 0 | 986 | 0 % |
| **Усяго** | **50 241** | **94 430** | **53.2 %** |

## Усталяванне

1. Скапіруйце змесціва `mod/` у каранёвую папку гульні, каб атрымалася:
   ```
   The Witcher 3\Mods\mod000_Belarusian\content\en.w3strings
   The Witcher 3\Mods\modBelarusianFont\content\blob0.bundle   (гл. «Шрыфт» ніжэй)
   ```
2. У гульні: **Settings/Настройки → Language/Локализация → English/Английская**.
3. Неперакладзеныя радкі аўтаматычна паказваюцца на англійскай.

> **Шрыфт / Font.** Стандартны англійскі шрыфт гульні не змяшчае кірыліцы, таму
> патрэбны мод на шрыфт, які дадае кірылічныя сівалы (уключна з
> беларускімі **і**, **ў**). Ён засноўваецца на шрыфце з [украінскай лакалізацыі
> (Nexus mod 8395)](https://www.nexusmods.com/witcher3/mods/8395) і таму **не
> ўваходзіць у гэты рэпазіторый** — спампуйце ўкраінскі моўны пак і скапіруйце ягоны
> `modUkrFont` як `modBelarusianFont` (тэчка `content/` з `blob0.bundle` і
> `metadata.store`). Падзяка аўтарам украінскага пераклада.

## Структура / Layout

```
data/            паралельныя дадзеныя перакладу (en / ru / pl / bel) па файлах гульні
  content0.json  …  content4.json
mod/             гатовы да ўсталявання мод (толькі тэкст)
  mods/mod000_Belarusian/content/en.w3strings
tools/           скрыпты зборкі
  build_mod.py   data → CSV → .w3strings (праз w3strings encoder)
  overrides.json ручныя праўкі, што перажываюць паўторны экспарт з Crowdin
```

### Фармат дадзеных

Кожны ключ — гэта `<id>_<keyhash>` са строкавай базы гульні; значэнне змяшчае
арыгінал і пераклады:

```json
{
  "1055110_231374e3": {
    "en": "Skelliger",
    "ru": "Островитянин",
    "pl": "Skelligijczyk",
    "bel": "Скелігчанін"
  }
}
```

## Зборка

```bash
python tools/build_mod.py --encoder path/to/w3strings.exe
# → mod/mods/mod000_Belarusian/content/en.w3strings
```

`build_mod.py` бярэ `bel` з `data/*.json`, прымяняе `tools/overrides.json`,
ачышчае пераносы радкоў і кадуе ў `.w3strings` праз
[w3strings encoder v0.4.1](https://www.nexusmods.com/witcher3/mods/1055).

## Падзякі

- Перакладчыкі супольнасці на Crowdin.
- Рудзі.
- Шрыфт кірыліцы — з [украінскай лакалізацыі The Witcher 3](https://www.nexusmods.com/witcher3/mods/8395).
- [w3strings encoder v0.4.1](https://www.nexusmods.com/witcher3/mods/1055).

## Ліцэнзія / License

Тэкст гульні належыць CD PROJEKT RED. Гэта некамерцыйны фанацкі пераклад.
