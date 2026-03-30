# ProMat - Osnova a vysvetlivky pre speakera

## 1. Osnova prezentacie (odporucany tok)
1. Problem a motivacia (preco tento projekt vznikol).
2. Ciele projektu (co ma aplikacia riesit v praxi).
3. Technologie a architektura (na com to bezi a preco).
4. Datovy model (ako su data prepojene).
5. Klucove funkcie:
   - autentifikacia a roly,
   - projekty a ulohy,
   - dokumenty a AI chat,
   - dashboard.
6. Zhrnutie a dalsie kroky.

Odporucana dlzka: 8-12 minut.

## 2. Poznamky k jednotlivym slajdom

### Slide 1 - Titulna strana
- Predstav sa, nazov projektu, skola a co bolo cielom maturitnej prace.
- Jedna veta: "Vytvoril som lokalny system, ktory spaja projektove riadenie a AI pracu nad dokumentmi."

### Slide 2 - Osnova
- Strucne povedz, co posluchaci uvidia.
- Pomaha to komisii orientovat sa a vnimat strukturu.

### Slide 3 - Problem a motivacia
- Zdovodnenie: timy casto pouzivaju viac nastrojov naraz.
- Dolezite je vysvetlit realny problem: strata casu a slaba prehladnost.

### Slide 4 - Hlavne ciele projektu
- Vyslov 5 cielov po jednom.
- Zvlast zdorazni lokalnu prevadzku a ochranu dat.

### Slide 5 - Technologie
- Vysvetli preco Flask: jednoduchy, rychly na vyvoj, dobra modularita.
- Vysvetli preco SQLite: vhodne pre skolsky projekt, jednoducha sprava.
- Pri AI spomen, ze model bezi lokalne cez Ollama.

### Slide 6 - Architektura aplikacie
- Vysvetli pojem blueprint: modul pre konkretne oblasti funkcionality.
- Popis tok poziadavky:
  1) pouzivatel klikne v UI,
  2) route v blueprinte spracuje vstup,
  3) servisna vrstva vykona logiku,
  4) DB sa aktualizuje,
  5) sablona vrati vystup.

### Slide 7 - Datovy model
- Dolezite vztahy:
  - Project 1:N Task,
  - Project 1:N Document,
  - User 1:N Task (assignee),
  - ChatSession 1:N ChatMessage.
- Povedz, ze tento model umoznuje auditovatelnost a historiu.

### Slide 8 - Autentifikacia a roly
- Ako to funguje:
  1) registracia/prihlasenie,
  2) heslo sa uklada ako hash,
  3) po prihlaseni sa drzi session,
  4) rola rozhoduje, co pouzivatel vidi a moze vykonat.
- Priklad: bezne roly nevidia manazerske akcie.

### Slide 9 - Sprava projektov a uloh
- Vysvetli hlavny workflow:
  1) vytvorenie projektu,
  2) pridanie uloh,
  3) priradenie ludom,
  4) sledovanie stavu v tabulke alebo kanbane,
  5) komentovanie a aktualizacie.
- Spomen drag-and-drop v kanbane ako prakticku ukazku UX.

### Slide 10 - Dokumenty a AI chat
- Vysvetli pipeline dokumentu:
  1) upload PDF/DOCX,
  2) extrakcia textu,
  3) ulozenie metadata + textu,
  4) AI chat pracuje s extrahovanym obsahom.
- Pri odpovediach zdorazni citacie ako overitelnost.

### Slide 11 - Dashboard a prinosy
- Dashboard je "jedna obrazovka pre rozhodovanie".
- Vysvetli biznis hodnotu: menej prepinania medzi nastrojmi, rychlejsie odpovede, lepsi prehlad o stave prace.

### Slide 12 - Zhrnutie
- Toto je klucovy slide pre maturitnu komisiu.
- Strucne zopakuj:
  1) co bolo vytvorene,
  2) co funguje dnes,
  3) aka je prakticka hodnota,
  4) co by bolo dalsie vylepsenie.

### Slide 13 - Otazky
- Udrz kontakt s komisiou, kludne tempo.
- Bud pripraveny na otazky: bezpecnost, AI presnost, skalovanie, dalsi vyvoj.

## 3. Kratky "script" (90 sekundove jadro)
"Projekt ProMat som vytvoril ako lokalnu webovu aplikaciu, ktora spaja spravu projektov a uloh s pracou nad dokumentmi pomocou AI. Pouzivatel moze riadit ulohy v tabulke aj kanbane, nahravat PDF a DOCX subory, a nasledne nad ich obsahom viest chat so sumarizaciou a citaciami. System je postaveny na Flasku, SQLAlchemy a SQLite, s modularnou architekturou cez blueprinty. Najvacsim prinosom je rychlejsie ziskavanie informacii a centralny prehlad o stave projektov, pricom data ostavaju lokalne. V dalsom kroku by som riesil pokrocile metriky AI kvality a notifikacie v realnom case."