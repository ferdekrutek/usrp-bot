# Obywatel Bot — instrukcja wdrożenia

Bot Discord do zarządzania obywatelami, podaniami na Senatora/Reprezentanta,
wyborami, stopniami naukowymi i partiami. Wszystkie dane trzymane są w
Firebase Realtime Database, więc **przetrwają każdy redeploy i restart**
na Render.

## Struktura projektu
```
obywatel-bot/
├── main.py                  # punkt startowy
├── config.py                # zmienne środowiskowe + listy partii/stopni
├── firebase_client.py       # komunikacja z Firebase
├── roblox_api.py            # weryfikacja nazwy Roblox
├── ssn_utils.py             # generowanie SSN
├── permissions.py           # sprawdzanie uprawnień admina
├── keep_alive.py            # mini-serwer HTTP dla Render (free tier)
├── cogs/
│   ├── verification.py      # panel weryfikacji Roblox
│   ├── applications.py      # panel podań Senator/Reprezentant
│   ├── elections.py         # /wybory otworz|zamknij|status
│   ├── degrees.py           # /stopien nadaj
│   ├── citizen.py           # /postac
│   └── party.py             # /zmien-partie
├── requirements.txt
├── render.yaml
└── .env.example
```

## Krok 1 — Firebase
Jeśli masz już bazę Firebase z gry Roblox, możesz użyć tej samej — bot
zapisuje dane pod innymi ścieżkami (`citizens`, `applications`, `settings`,
`ssn_index`), więc nie kolidują z `codes`/`votes` z gry.

Jeśli tworzysz nową:
1. https://console.firebase.google.com → nowy projekt → **Realtime Database**.
2. Skopiuj URL bazy (`https://twoj-projekt-default-rtdb.firebaseio.com`).
3. Na start ustaw reguły testowe (`.read`/`.write`: `true`) — **przed
   wystawieniem bota na produkcję ogranicz je**, bo każdy znający URL może
   inaczej edytować dane bezpośrednio.

## Krok 2 — Bot na Discordzie
1. https://discord.com/developers/applications → **New Application**.
2. Zakładka **Bot** → **Reset Token** → skopiuj token (to `DISCORD_TOKEN`).
3. W tej samej zakładce włącz **Server Members Intent** (bot potrzebuje go
   do nadawania ról).
4. Zakładka **OAuth2 → URL Generator**: zaznacz `bot` oraz `applications.commands`,
   z uprawnień zaznacz co najmniej `Manage Roles`, `Send Messages`,
   `Embed Links`. Wygenerowanym linkiem zaproś bota na serwer.
5. **Ważne:** rola bota na liście ról serwera musi być **wyżej** niż role
   `Zweryfikowany`, `Obywatel`, `Senator`, `Reprezentant` — inaczej nie
   będzie mógł ich nadawać.

## Krok 3 — ID ról i kanałów
Włącz w Discordzie tryb developera (Ustawienia → Zaawansowane → Tryb
developera), kliknij prawym na rolę/kanał → **Kopiuj ID** i uzupełnij:
- `ROLE_VERIFIED_ID`, `ROLE_CITIZEN_ID` — role nadawane po weryfikacji.
- `ROLE_SENATOR_ID`, `ROLE_REPRESENTATIVE_ID` — opcjonalne, nadawane po
  akceptacji podania (zostaw `0`, jeśli nie chcesz automatycznego nadawania).
- `ADMIN_ROLE_ID` — rola uprawniona do komend administracyjnych (opcjonalne,
  jeśli masz uprawnienie „Zarządzaj serwerem”, i tak zadziała).
- `APPLICATIONS_REVIEW_CHANNEL_ID` — kanał, na który trafiają podania do
  akceptacji.

## Krok 4 — GitHub
```bash
cd obywatel-bot
git init
git add .
git commit -m "Pierwsza wersja bota"
git branch -M main
git remote add origin https://github.com/TWOJ-LOGIN/obywatel-bot.git
git push -u origin main
```
Plik `.env` jest w `.gitignore` — token i sekrety **nigdy** nie trafiają do
repozytorium. Wpisujesz je bezpośrednio w panelu Render (krok 5).

## Krok 5 — Render
1. https://dashboard.render.com → **New → Web Service** → połącz repo z GitHub.
2. Render wykryje `render.yaml` i podstawi ustawienia automatycznie (albo
   ustaw ręcznie: Build Command `pip install -r requirements.txt`,
   Start Command `python main.py`).
3. W zakładce **Environment** uzupełnij wszystkie zmienne z `.env.example`
   (token, URL Firebase, ID ról/kanału).
4. Deploy. W logach powinno pojawić się „Zalogowano jako …”.

### Ważne — 24/7 na Render
Sprawdziłem aktualny cennik Render (sierpień 2026):
- **Darmowy plan Web Service usypia proces po 15 minutach bez ruchu HTTP.**
  Uśpienie bota = utrata połączenia z Discordem, aż coś go „obudzi”.
  Plik `keep_alive.py` wystawia adres `/`, który możesz co 5 minut pingować
  darmowym serwisem typu UptimeRobot — to popularny, ale nieformalny
  obchodzący sposób i Render może to kiedyś ograniczyć.
- **Plan Starter (od $7/mies.)** usuwa usypianie całkowicie — to najbardziej
  pewna opcja dla bota, który ma działać naprawdę bez przerw.
- Render zmienia czasem szczegóły cenowe — przed decyzją zerknij na
  https://render.com/pricing, żeby potwierdzić aktualne warunki.

## Wystawianie paneli na serwerze
Po wdrożeniu, na kanale, gdzie mają się znaleźć panele:
- `/panel-weryfikacja` — wystawia embed z przyciskiem weryfikacji Roblox.
- `/panel-senat` — osobny embed z przyciskiem „Aplikuj na Senatora”.
- `/panel-izba` — osobny embed z przyciskiem „Aplikuj na Reprezentanta”.

Wszystkie panele działają nawet po restarcie bota — przyciski mają stałe
`custom_id`, a oczekujące podania są odtwarzane z Firebase przy starcie.

Komendy `/panel-weryfikacja`, `/panel-senat`, `/panel-izba`, `/wybory otworz`,
`/wybory zamknij` i `/stopien nadaj` są ukryte w menu komend dla osób bez
uprawnienia „Zarządzaj serwerem” (Discord robi to automatycznie na
podstawie `default_permissions` w kodzie) — zwykli użytkownicy w ogóle
ich nie zobaczą we wpisywanym `/`.

## Lista komend
| Komenda | Kto używa | Co robi |
|---|---|---|
| `/panel-weryfikacja` | admin | Wystawia panel weryfikacji Roblox |
| `/panel-senat` | admin | Wystawia panel podań na Senatora |
| `/panel-izba` | admin | Wystawia panel podań na Reprezentanta |
| `/wybory otworz` | admin | Otwiera wybory (flaga w Firebase) |
| `/wybory zamknij` | admin | Zamyka wybory |
| `/wybory status` | każdy | Sprawdza status wyborów |
| `/stopien nadaj` | admin | Nadaje stopień naukowy obywatelowi |
| `/postac` | każdy | Pokazuje profil postaci po nicku Discord ALBO po SSN (imię, nazwisko, stopień, partia, zamieszkanie, SSN) |
| `/zmien-partie` | obywatel | Zmienia własną przynależność partyjną (aktualizuje też nick) |

## Nick na serwerze
Po weryfikacji, po złożeniu podania do Senatu/Izby i po `/zmien-partie`,
bot ustawia nick w formacie `[TAG] Imię Nazwisko`, np. `[REP.] Jan Kowalski`.
Tagi (edytowalne w `config.py` pod `PARTY_TAGS`): `DEM.` (Partia
Demokratyczna), `REP.` (Partia Republikańska), `LIB.` (Partia
Libertariańska — dodałem ten tag, bo partia jest na liście, ale nie
podałeś dla niej skrótu; zmień w `config.py`, jeśli chcesz inny),
`BEZP.` (Niezależny, domyślnie po weryfikacji).

Żeby to zadziałało, **rola bota musi być wyżej niż rola najwyższej rangi
każdego obywatela** (tak samo jak przy nadawaniu ról) — inaczej Discord
zablokuje zmianę nicku i bot po prostu to zaloguje bez wywalania błędu.
Discord nigdy nie pozwala botom zmieniać nicku właściciela serwera —
to ograniczenie samego Discorda, nie da się go obejść.

## Dodawanie kolejnych funkcji w przyszłości
Projekt jest podzielony na cogi — każda funkcja to osobny plik w `cogs/`.
Żeby dodać nową funkcję:
1. Stwórz `cogs/nowa_funkcja.py` z klasą `commands.Cog` (lub `GroupCog` dla
   grupy komend) i funkcją `async def setup(bot)` na końcu.
2. Dopisz `"cogs.nowa_funkcja"` do listy `EXTENSIONS` w `main.py`.
3. Commit + push na GitHub — Render sam zrobi redeploy.

Listę partii (`PARTIES`) i stopni naukowych (`DEGREES`) edytujesz w jednym
miejscu — `config.py`.
