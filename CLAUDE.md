# CLAUDE.md — KauppaAgentit (TradingAgents Suomi-fork)

## Projektin yleiskuvaus
Suomalainen fork [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) — Python multi-agent LLM-kaupankäyntiframework. Meidän versio: suomenkielinen UI, OMXH-tuki, suomalainen verotuskonteksti, kuluttajaystävällinen. Lisenssi: Apache-2.0.

## VASTUUVAPAUTUS (pakollinen kaikkialla)
Tutkimus-/oppimistarkoitus. EI sijoitusneuvontaa. Suomen lain mukaan sijoitusneuvonta vaatii Fivan toimiluvan. UI:ssa AINA: *"Tämä on AI:n tuottama analyysi, ei sijoitussuositus."*

**Pakolliset vastuuvapautuslauseet:**
- **Lyhyt** (joka raportti): "Tämä on AI:n tuottama analyysi, ei sijoitussuositus. Tee sijoituspäätökset oman harkintasi mukaan."
- **Pitkä** (rekisteröityminen/asetukset): "KauppaAgentit on tekoälyyn perustuva analyysityökalu tutkimus- ja oppimistarkoituksiin. Palvelu EI ole Finanssivalvonnan valvomaa sijoitusneuvontaa. AI-analyysin tulokset voivat olla virheellisiä tai vanhentuneita. Sijoittamiseen liittyy aina riski pääoman menettämisestä."

## Muistiinpanoja Claudelle

### Session aloitus ja lopetus
- **AINA** lue CLAUDE.md ennen kuin teet mitään — se on projektin ainoa totuuslähde
- **AINA** päivitä Kehityksen vaiheet -checkboxit kun tehtävä valmistuu
- Jos teet muutoksen joka vaikuttaa arkkitehtuuriin, päivitä myös relevantti kohta CLAUDE.md:ssä

### Regulaatio
- AINA vastuuvapautus mukana — tämä EI OLE sijoitusneuvontaa
- ÄLÄ käytä: "suosittelen", "kannattaa ostaa/myydä"
- KÄYTÄ: "agentit analysoivat", "analyysin tulos", "OSTA-signaali / PIDÄ-signaali / MYY-signaali"
- Jokainen päätös on signaali, ei suositus

### Visuaalinen tyyli ja sävy
- **EI emojeja** missään — ei koodissa, ei UI-teksteissä, ei agenttiraporteissa, ei Telegram-viesteissä, ei CLAUDE.md:ssä
- Sävy on ammattimainen ja asiallinen läpi koko tuotteen: raportit, bottiviestit, UI-komponentit, virheilmoitukset
- Käytä selkeitä tekstimerkintöjä emojejen sijaan: "[OSTA-SIGNAALI]", "[VAROITUS]", "[VALMIS]" jne.
- Vältetään liian tuttavallista tai markkinahenkistä kieltä — tuote on analyysityökalu, ei pelisovellus

### Yleinen
- Tämä on FORK — muokkaa upstreamia mahdollisimman vähän, lisää omat tiedostot
- Käytä context7-MCP:tä LangGraph-dokumentaatioon ennen kuin muokkaat graph-koodia
- Käytä claude-context MCP:tä kun etsit upstreamin koodista tiettyä logiikkaa
- Kohderyhmä on **suomalainen peruskäyttäjä** — ei DBA, ei quant, ei devaaja

### Tekninen
- Suosi Anthropic-malleja (Claude) LLM-providerina — se on meidän ympäristö
- `deep_think_llm = claude-haiku-4-5-20251001` testaus (~€0.05/ajo), vaihda Sonnetiin tuotannossa (~€1.50+/ajo)
- Älä tee turhia muutoksia upstream-tiedostoihin — helpompi synkata myöhemmin
- Testaa AINA suomalaisilla osakkeilla: NOKIA, NORDEA, NESTE, UPM, KONE
- EUR-denominaatio kaikkialla, ei dollareita
- Docker-ympäristö AINA — ei asenneta suoraan host-koneelle
- Uutisanalyytikko käyttää `get_all_stock_news_combined` (1 tool call, ei 3 erillistä)

### Priorisointi
Toimiva fork ensin → lokalisointi → Telegram-botti → Web-UI → creditit → portfolio → B2B.
Jokainen vaihe pitää olla itsenäisesti julkaistavissa. **Telegram-botti on nopein tie käyttäjiin ja palautteeseen.**

## Tech Stack
- **Backend:** Python 3.13+, LangGraph, FastAPI
- **LLM:** Anthropic Claude (Haiku testaus, Sonnet tuotanto), OpenAI, Ollama
- **Data:** Yahoo Finance, Alpha Vantage, OMXH (`omxh_utils.py`), Kauppalehti/YLE RSS
- **Frontend:** React 18 + Vite + Tailwind + WebSocket
- **Infra:** Docker Compose, PostgreSQL 16, Redis 7

## Avaintiedostot (älä toista sisältöä tässä)
- `tradingagents/finnish_config.py` — FINNISH_CONFIG (llm_provider, locale, tax_context, news_sources)
- `fi_prompts/` — 9 suomenkielistä agenttipromptia
- `tradingagents/dataflows/omxh_utils.py` — Helsingin pörssin data (.HE-suffiksi, OMXH_TICKERS)
- `db/init/001_schema.sql` — analyysit, agentti_raportit, llm_cache, api_kustannukset
- `db/init/002_credits.sql` — kayttajat, credit_saldot, credit_tapahtumat, portfoliot, hälytykset
- `credits/pricing.py` — CREDIT_COSTS, SUBSCRIPTION_TIERS
- `integrations/vero/paaomavero.py` — verolaskuri
- `bot/telegram_bot.py` — Telegram-botti
- `docker-compose.yml` — db + redis + app + db-cleanup

## MCP-säännöt
1. **Context7 ENSIN** — LangGraph/Rich/tradingagents-koodi → tarkista ajantasainen API
2. **Claude-context** — upstreamin logiikan etsiminen forkkia varten
3. **Postgres-MCP** — jokainen analyysiajo tallennetaan
4. **Desktop-commander** — propagate()-ajot (>30s)
5. **Memory** — sessioyhteenvedot

## Agenttiflow
**Rinnakkain:** Fundamentti → Sentimentti → Uutiset → Tekninen  
**Väittely:** Bull ↔ Bear (`max_debate_rounds`, oletus 1, tuotanto 2–3)  
**Päätös:** Kauppias → Riskienhallinta → Salkunhoitaja → OSTA/PIDÄ/MYY + vastuuvapautus

## OST-rajoite (agenttien on tunnettava!)
OST sallii: OMXH-osakkeet, First North. **Kielletty: ETF, indeksirahastot, joukkovelkakirjat.** Raja 100 000€. Vero realisoituu nostohetkellä, ei myyntihetkellä.  
**Salkunhoitaja EI SAA suositella ETF:iä OST-käyttäjälle — se olisi faktisesti väärä neuvo.**

## Käyttäjäsegmentit (UI:ssa valinta)
- **OST** → agentit tietävät kiellot ja verolykkäysedun; Rahastoagentti piilotetaan
- **AOT** → normaali verotuslogiikka; kaikki agentit näkyvissä
- **Pääosin rahastosijoittaja** → Rahastoagentti (`analysts/funds.py`) etualalle

## Kustannusarvio per analyysi
Täysi analyysi (kaikki agentit, 1 väittelykierros, max_tokens=2048).
Mitattu Nokia-analyysillä 2026-03-25 ilman max_tokens-rajoitusta: ~$0.30 (Haiku).
Optimointien jälkeen (max_tokens=2048 + uutissummaryjen katkaisu 300 merkkiin):
- Claude Haiku: ~€0.05–0.10/analyysi (arvio)
- Claude Sonnet: ~€0.30–0.50/analyysi (arvio)
- Pro-taso (200 analyysiä/kk Haikulla): kulut ~€10–20/kk — tarkista ennen hinnoittelua
- Ilmainen taso (3/kk): kulut ~€0.15–0.30/käyttäjä/kk
Tokenien hallinta: `max_tokens=2048` FINNISH_CONFIGissa, `TEST_MODE=true` ylikirjoittaa arvolla 500.

## Regulaatio ja juridinen status
Työkalu myydään analyysityökaluna (kuten TrendSpider, Inderesin analyysit), **ei** sijoitusneuvontana. Ei vaadi Fiva-toimilupaa kunhan:
- Ei anneta yksilöllistä suositusta ("sinun kannattaa ostaa")
- Käytetään aina yleisluontoista muotoa
- Vastuuvapautus AINA näkyvissä
- Ei luvata tuottoja

**Ennen lanseerausta:** Ota yhteyttä Finanssivalvonnan Innovation Help Deskiin (maksuton) → pyydä ennakollinen arvio.

## Koodauskäytännöt
- Python 3.13+, type hints, async/await, docstringit suomeksi
- Upstream-muutokset minimiin — merkitse `# FORK: Suomi-lokalisointi`
- React: Tailwind, kaikki UI-tekstit `i18n/fi.json`, loading-tilat + error boundaryt joka agenttinäkymälle
- Git-branchit: `feature/sentimentti-kauppalehti`, `fix/omxh-data`, `ui/dashboard`
- Upstream-synk: `git fetch upstream && git merge upstream/main`

## Tietoturva
- `.env` EI versionhallintaan
- API-avaimet vain palvelinpuolella, ei frontendiin
- Ticker-validointi (vain OMXH/tunnetut)
- Rate limiting LLM-kutsuihin

## Parannusideat ja tulevat ominaisuudet

### Rahasto- ja ETF-agentti (vain AOT-käyttäjille)
- Rakenna `analysts/funds.py` — vertailee Seligsonin, Nordnetin superrahastojen ja ETF:ien TER-kulua, hajautusta, historiallista tuottoa
- Näyttää rankingin: "matala kulu / laaja hajautus / Suomi-paino"
- EI koskaan näy OST-käyttäjille

### Käsitteiden kansantajuistaminen
- Luo `docs/termit.md` — suomenkieliset selitykset: P/E, P/B, beta, volatiliteetti, osinkotuotto, free cash flow
- Web-UI:ssa jokaisen teknisen termin vieressä info-ikoni → tooltip
- Telegram: `/termi <nimi>` → lyhyt selitys suomeksi

### Tietosuoja ("Pankkitason turvallisuus" -narratiivi)
Lisää etusivulle ja `docs/regulaatio.md`:ään:
- Ei kerätä pankkitunnuksia tai henkilötunnuksia
- Portfolio syötetään manuaalisesti tai Nordnet-integraation kautta
- Kaikki data pysyy EU:ssa (esim. Hetzner Helsinki)
- Käyttäjädata ei myydä eteenpäin
- Käyttäjä voi poistaa kaiken datansa (GDPR Art. 17)

### Realistiset analyysimäärät tilauksittain (TARKISTA hinnoittelu!)
Yksi täysi analyysi maksaa API-kuluissa ~0.10–0.40€. Alla realistisemmat rajat:

| Taso | Analyysit/kk | Hinta | Marginaali-arvio |
|------|-------------|-------|-----------------|
| Ilmainen | 3 (ei 30) | 0€ | -0.60–1.20€/kk |
| Perus | 20 (ei 30) | 19€ | ~11–15€/kk |
| Pro | 80 (ei ∞) | 49€ | ~17–25€/kk |
| Business | 300 | 149€ | ~20–60€/kk |

---

## Kehityksen vaiheet

### Vaihe 1: Fork + lokalisointi ✅
- [x] Fork, upstream remote, `finnish_config.py`
- [x] `fi_prompts/` — kaikki 9 agenttia vastaavat suomeksi (`prompt_loader.py`)
- [x] Nokia-analyysi: SELL @ €6.87 (2026-03-24) ✓
- [x] `max_tokens=2048` lisätty FINNISH_CONFIGiin — kustannushallinta (mitattu ~$0.30 → ~€0.05–0.10)
- [x] `research_manager.py` englanninkielinen prompt korjattu — `fi_prompts/research_manager_system.md` luotu (10. Finnish-prompt)
- [x] fi_prompts suomen kielen tarkistus: 4 kielivirhettä korjattu (osingonpeite, pitkäaikaiset, perusteettoman, Regulaatioriski)
- [x] Strukturoitu "Avainhavainnot"-osio lisätty 6 analyytikkopromptiin (fundamentals, news, sentiment, technical, bull, bear) — Vaihe 3.5 pohja
- [x] CLI `fi`-komento: `python -m cli.main fi` — kysyy vain tickerin, käyttää FINNISH_CONFIGia
- [x] CLI Windows UTF-8 enkoodauskorjaus — kaikki tiedostokirjoitukset `encoding="utf-8"`
- [x] RSI/MACD/Bollinger raja-arvokorjaus (2026-03-26) — `fi_prompts/technical_system.md`:ään lisätty eksplisiittinen tulkintataulukko (RSI <30 ylimyyty, >70 ylinostettu, 30–70 neutraali) LLM-virhetulkintojen estämiseksi
- [x] Teknisen analyysin cache-esto (2026-03-26) — `CACHE_CONFIG` lisätty `finnish_config.py`:hin TTL=0 avaimille `technical_`, `rsi_`, `macd_`, `bollinger_` — aikasarjalaskelmat eivät saa jäädä cacheen
- [ ] Docker Compose -ympäristö pystyyn (PostgreSQL + Redis + app)

### Vaihe 1.5: AI Act & Compliance (PAKOLLINEN ennen julkaisua)
- [ ] Selvitä onko "korkean riskin AI-järjestelmä" — Fiva valvoo rahoitussektorin AI:ta 2026
- [ ] Lisää `docs/regulaatio.md`:ään erillinen AI Act -osio
- [ ] Varmista koneluettava disclaimer jokaisessa ulos lähtevässä raportissa
- [ ] Luo `compliance_log`-taulu PostgreSQL:ään (timestamp, mallit, konfiguraatio, hash)
- [ ] `COMPLIANCE_MODE`-ympäristömuuttuja: OSTA/PIDÄ/MYY → "Positiivinen/Neutraali/Negatiivinen näkymä"

### Vaihe 2: OMXH-data + suomalaiset lähteet
- [x] `omxh_utils.py`, `get_finnish_news`, Kauppalehti+YLE RSS, LRU-cache
- [x] `get_all_stock_news_combined` (1 tool call, ei 3 erillistä), OMXH_KEYWORDS-kartta
- [x] Uutisartikkelimäärä 20 → 15, summary katkaisu 300 merkkiin (API-kustannusten hallinta)
- [ ] Testaa: Nokia ✓, KONE ✓ (osittain), Nordea, Neste, UPM

### Vaihe 2.5: Laatu- ja regressiotestit
- [ ] `tests/test_backtests/` — stabiliteestitestit (NOKIA, NESTE, NORDEA, KONE eri parametreilla)
- [ ] "Golden baseline" -fixturet: `tests/fixtures/baseline_<ticker>_<pvm>.json` — regressiotestit isoja prompti/mallipäivityksiä varten
- [ ] Automaattinen suomen kielen laadun tarkistus mallipäivitysten jälkeen (ei englanninkielisiä vastauksia)
- [x] Token-ylärajat agenttiraporteille — `max_tokens=2048` FINNISH_CONFIGissa, `500` TEST_MODEssa

### Vaihe 2.75: Suomi-spesifiset datasignaalit (tunnistettu 2026-03-25)
Parannukset jotka erottaisivat kilpailijoista — ilmaisia lähteitä joita kukaan muu ei käytä automaattisesti.
- [x] `get_insider_transactions` kytkentä `fundamentals_analyst.py` tools-listaan (1 rivi, tool on jo olemassa)
- [ ] Finanssivalvonnan sisäpiiri-ilmoitukset XML-feedinä — johdon ostot/myynnit aggregoituna fundamenttianalyytikkoon
- [ ] Inderes-konsensuksen vertailu — portfolio manager vertaa signaalia Inderesin julkiseen suositukseen (käyttöehdot tarkistettava)
- [ ] Osinko- ja tuloskalenteri — Euronext Helsingin virallinen kalenteri kontekstiksi analyysiin
- [ ] Valuuttariskin eksplisiittinen mallinnus riskiagenttiin — Nokia/KONE/Neste USD/CNY-altistus
- [ ] Euroclear Finland omistusmuutokset — liputusilmoitukset institutionaalisten liikkeiden signaalina

### Vaihe 3: Telegram-botti
- [x] `/analysoi NOKIA` toimii — callbacks `graph.invoke()`lle, formatter (parse_decision, markdown-siivous)
- [x] Whitelist-pohjainen pääsynhallinta (`TELEGRAM_WHITELIST` env var)
- [x] `/salkku` → käyttäjän seurantalista (`telegram_bot/salkku.py`)
- [x] `/halytys NOKIA -5%` → hälytys (`telegram_bot/halytys.py`)
- [ ] Markkinointi: suomalaiset sijoitus-Telegram-ryhmät

**Telegram-botin flow:**

/analysoi NOKIA
→ tarkista credit-saldo
→ käynnistä TradingAgentsGraph.propagate()
→ lähetä "Agentit analysoivat Nokiaa..."
→ päivitä viesti agentti kerrallaan:
"Fundamenttianalyysi valmis."
"Sentimenttianalyysi valmis."
"Tutkijat analysoivat vastakkaisia näkemyksiä..."
"Kauppias on tehnyt ehdotuksen."
"Riskianalyysi valmis."
→ lähetä lopullinen tulos:
"NOKIA AI-analyysi 24.3.2026
[OSTA-SIGNAALI] | Luottamus: 72%
Fundamentit vahvat...
[RISKIT] Valuuttariski USD/EUR
[VEROHUOMIO] Jos myyt 100 kpl @ 4.80 EUR...
Tämä EI ole sijoitusneuvontaa."
→ vähennä 1 credit



### Vaihe 3.5: Explainable AI (kriittinen käyttäjäluottamukselle)
> Siirretty aiemmaksi — suomalainen käyttäjä ei luota pelkkään "OSTA"-vastaukseen.
- [x] Pakota rakenteiset "Avainhavainnot"-osiot per agentti — lisätty kaikkiin 6 analyytikkopromptiin:
  - Fundamenttiagentti: Top 3 vahvuudet + Top 3 riskit + kriittisin epävarmuus
  - Uutisagentti: Top 3 positiiviset + Top 3 negatiiviset uutiset
  - Sentimenttiagentti: Top 3 positiiviset + Top 3 negatiiviset signaalit
  - Tekninen analyytikko: Top 3 tekniset signaalit + riskitasot
  - Bull-tutkija: Top 3 perustelut + tunnistetut riskit + kriittisin katalyytti
  - Bear-tutkija: Top 3 perustelut + vastaavat skenaariot + kriittisin riski
- [ ] Telegram: "Nayta perustelut" -inline-nappi (callback query)
- [ ] Web-UI: collapsible "Nayta tarkat perustelut" -paneeli (oletuksena suljettu)

### Vaihe 4: Web-dashboard + käyttäjätilit
- [ ] React + FastAPI + WebSocket
- [ ] Käyttäjärekisteröinti (email tai Suomi.fi-tunnistautuminen)
- [ ] Agenttien etenemisen reaaliaikaseuranta
- [ ] Analyysien historia ja vertailu
- [ ] Vastuuvapautus-komponentti (pakollinen joka näkymässä)

### Vaihe 4.5: Onboarding + riskiprofilointi
- [ ] Onboarding-wizard (max 2 kysymystä ensimmäisellä kirjautumisella):
  - Kokemus: "Aloittelija / Kokenut sijoittaja"
  - Riskinsieto: "Matala / Keskitaso / Korkea"
- [ ] MiFID II -vastuuvapautus pakollinen ennen ENSIMMÄISTÄ analyysiä (ei vain kerran rekisteröinnissä)
- [ ] `kayttajat`-tauluun: `kokemus_taso`, `riski_profiili`, `disclaimer_hyvaksytty_at`, `tili_tyyppi` (OST/AOT/rahastot)
- [ ] `portfolio_mgr`-agentti muotoilee sävyn riskiprofiilin mukaan (aloittelijalle korostetaan hajautusta)

### Vaihe 5: Credit-järjestelmä + Stripe
- [ ] Tilaustasot: Ilmainen 0€ (30cr) / Perus 19€ (120cr) / Pro 49€ (500cr) / Business 149€ (∞)
- [ ] Stripe EU/SEPA-integraatio
- [ ] API-kustannusten seuranta per käyttäjä
- [ ] Kuukausittainen budjettikatto per käyttäjä

### Vaihe 6: Portfolioseuranta + hälytykset
- [ ] Manuaalinen salkku (käsin syöttö)
- [ ] Nordnet External API -integraatio — automaattinen salkkusynkronointi
  - API: `https://public.nordnet.se/api/2` (dokumentaatio: https://www.nordnet.fi/externalapi/docs/api)
  - Auth: per-käyttäjä session ID (käyttäjä kirjautuu Nordnetiin → OAuth-flow)
  - Endpointit: GET /accounts (positiot), GET /accounts/{id}/positions, GET /instruments (haku ISIN:llä)
  - Huom: ei community/sosiaalinen data — pelkkä portfolio ja markkinadata
- [ ] Hälytysten seurantatapahtumat: hinta yli/ali raja, sentimenttimuutos, tekninen signaali, tulosjulkistus, uutistriggerit
- [ ] Monitorointiflow (15min sykli): hae hinnat → vertaa hälytyksiin → `notifier.py` (Telegram/email/push) + kerran päivässä kevyt sentimenttiskannaus
- [ ] Credit-kulutus: 0.1 cr/osake/päivä portfolioseurannasta

### Vaihe 6.5: Veroskenaario-simulaattori (Suomen tärkein differentiator)
- [ ] `paaomavero.py` skenaarioihin: "Myy nyt" vs "Myy 6kk päästä", hankintameno-olettama (20% jos <10v, 40% jos ≥10v), OST vs AOT konkreettisilla luvuilla
- [ ] Web-UI: "Verosimulaattori"-näkymä → taulukko: myyntihinta | luovutusvoitto | arvioitu vero | netto
- [ ] Salkunhoitaja lisää automaattisesti "[VEROHUOMIO]"-osion jos käyttäjällä osake salkussa voitollisena
- [ ] Telegram: `/vero NOKIA 200 3.80` laskee veroskenaarion suoraan chatissa

### Vaihe 7: Backtesting
- [ ] Historiallinen trackrecord-näkymä
- [ ] Vertailu OMXH-indeksiin ja Inderesin suosituksiin
- [ ] Vastuuvapautus backtesting-näkymässä: *"Historialliset tulokset eivät takaa vastaavia tuottoja tulevaisuudessa."*

### Vaihe 7.5: "Viikon OMXH-signaali" -automaatio
- [ ] Viikoittainen cron-job (maanantai 08:00 EET): skannaa OMXH TOP 25 sentimenttimuutokset → 1 mielenkiintoisin signaali → julkiselle Telegram-kanavalle
- [ ] Formaatti: lyhyt + napakka + linkki "Lue täysi analyysi KauppaAgenteilla"
- [ ] Toimii orgaanisena markkinointikanavana

### Vaihe 8: B2B White-label
- [ ] API-pohjainen versio pankeille/varainhoitajille
- [ ] Brändättävä dashboard, SLA, enterprise-tuki
- [ ] Yhteydenotto: Nordea, OP, Evli, Mandatum

### Vaihe 8.5: Jaettavat raportit
- [ ] `GET /api/jaa/<analyysi_id>` → anonyymi jaettava URL (ei tunnistetietoja)
- [ ] CTA jaettavassa raportissa: *"Analyysi tuotettu KauppaAgentit-työkalulla — kokeile ilmaiseksi: <url>"*
- [ ] Telegram: `/jaa` → jaettava linkki viimeisimmästä analyysistä
- [ ] `jaetut_raportit`-taulu (analyysi_id, token, luotu, katselukerrat) — seuraa orgaanista leviämistä