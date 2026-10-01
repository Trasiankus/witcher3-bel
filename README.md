# witcher3-bel — Беларуская лакалізацыя «The Witcher 3: Wild Hunt»

Belarusian localization of *The Witcher 3: Wild Hunt — Remastered* (v5.00).

Далучыцца да праекту можна тут: https://crowdin.com/project/witcher-3-bel

## Стан перакладу

| Частка | Перакладзена | Усяго | Адсотак |
|---|---:|---:|---:|
| Базавая гульня | 60 631 | 72 131 | **84.1 %** |
| Hearts of Stone | 0 | 6 606 | 0.0 % |
| Blood and Wine | 0 | 17 144 | 0.0 % |
| Іншыя DLC | 0 | 982 | 0.0 % |
| **Усяго** | **60 631** | **96 863** | **62.6 %** |
| Субтытры відэаролікаў | 25 | 178 | 14.0 % |

Лічыцца па тэксце Remastered (v5.00).

## Усталяванне

1. Скапіруйце тэчку `mod/mods/mod000_Belarusian` у `The Witcher 3\mods\`, каб атрымалася:
   ```
   The Witcher 3\mods\mod000_Belarusian\content\ua.w3strings
   ```
2. У гульні: **Settings → Language → Text language** — перасуньце на **Belarusian**
   (пасля пераключэння яна будзе называцца **Беларуская**).
3. Неперакладзеныя радкі паказваюцца на англійскай; агучванне застаецца англійскім.

> **Чаму на месцы ўкраінскай мовы?** Толькі ў гэтым слоце гульня бярэ субтытры
> відэаролікаў з файлаў, якія можа замяніць мод, і толькі ў ім шрыфт мае ўсе беларускія
> літары (**і**, **ў**) — таму асобны мод на шрыфт больш не патрэбны. Украінскімі
> застаюцца толькі надпісы, убудаваныя ў выявы (лагатып, папярэджанне на пачатку гульні).
> Калі ў вас застаўся `modBelarusianFont` ад ранейшых версій — яго можна выдаліць.

## Структура / Layout

```
data/              паралельныя дадзеныя перакладу (en / ru / pl / bel)
  content0.json … content13.json   базавая гульня, патчы, новыя радкі Remastered (content13)
  dlc/             dlcN / ep1 / bob    дадаткі (з'явяцца па меры перакладу)
  subtitles.json   субтытры відэаролікаў
mod/               гатовы да ўсталявання мод
  mods/mod000_Belarusian/content/
    ua.w3strings     увесь тэкст: беларускі, дзе перакладзена, астатняе — англійскі
    en.w3strings     назва мовы «Belarusian» у англійскім меню
    blob0.bundle, metadata.store   субтытры відэаролікаў
tools/             скрыпты зборкі
  build_mod.py     data → мод
  mod_layout.py    зборка мода (слот украінскай мовы)
  w3strings164.py  чытанне/запіс .w3strings (фармат Remastered: v164, UTF-8)
  w3bundle.py      зборка blob0.bundle + metadata.store
  movie_subs.py    субтытры відэаролікаў (.subs)
  overrides.json   ручныя праўкі, што перажываюць паўторны экспарт з Crowdin
```

### Фармат дадзеных

Кожны ключ — гэта `<id>_<keyhash>` са строкавай базы гульні (для субтытраў —
`<ролік>_<нумар>`); значэнне змяшчае арыгінал і пераклады:

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
python tools/build_mod.py --game "C:/Games/Steam/steamapps/common/The Witcher 3"
# → mod/mods/mod000_Belarusian/content/
```

`build_mod.py` бярэ `bel` з `data/*.json`, прымяняе `tools/overrides.json` і збірае мод.
Устаноўленая гульня патрэбная для англійскага тэксту (неперакладзеныя радкі) і таймінгаў
субтытраў відэа. Знешнія інструменты не патрэбныя — толькі Python 3.

## Падзякі

- Перакладчыкі супольнасці на Crowdin.
- Рудзі.
- Фармат `.w3strings` v164 — паводле [Witcher3StringEditor](https://github.com/0x7A2C9E5D/Witcher3StringEditor) (MIT).
- Фармат `metadata.store` — паводле [WolvenKit](https://github.com/WolvenKit/WolvenKit-7).
- Шрыфт ранейшых версій — з [украінскай лакалізацыі The Witcher 3](https://www.nexusmods.com/witcher3/mods/8395).

## Ліцэнзія / License

Тэкст гульні належыць CD PROJEKT RED. Гэта некамерцыйны фанацкі пераклад.
