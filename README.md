# blocklist

Zusammengefuehrte DNS-Allowlist fuer [Technitium DNS Server](https://technitium.com/dns/).

Fuehrt mehrere oeffentliche Whitelists zu **einer** Datei zusammen, normalisiert die
Formate, dedupliziert und filtert Eintraege heraus, die man nicht freigeben will.

## Einbinden in Technitium

Settings -> Blocking -> *Block List URLs*, mit `!` als Praefix:

```
!https://raw.githubusercontent.com/hennscho/blocklist/main/allowlist.txt
```

Danach im Dashboard den Zaehler **Allow List** pruefen. Steht dort `0`, wurde die
Liste nicht geparst — dann stimmt die URL oder das Format nicht.

## Aufbau

| Datei                       | Rolle |
|-----------------------------|-------|
| `allowlist.txt`             | **Ergebnis.** 449 Domains, autogeneriert, nicht von Hand bearbeiten. |
| `sources.txt`               | Upstream-URLs, die zusammengefuehrt werden. |
| `quarantine.txt`            | Eintraege aus den Upstreams, die bewusst *nicht* freigegeben werden. |
| `allowlist-local.txt`       | Eigene Ausnahmen. Gewinnt immer, wird von keinem Upstream ueberschrieben. |
| `build.py`                  | Der Build. Braucht nur Python 3.11+, keine Abhaengigkeiten. |
| `technitium-blocklists.txt` | Referenz: das passende Block-List-Set zum Reinkopieren. |

Lokal bauen:

```bash
python3 build.py
```

Der GitHub-Workflow macht dasselbe taeglich um 04:17 UTC und committet nur, wenn
sich etwas geaendert hat. Liefert ein Upstream weniger als 50 Eintraege, bricht er
ab statt eine leere Liste zu veroeffentlichen.

## Was der Build wegwirft

* Regex- und Wildcard-Eintraege (`(^|\.)example\.com$`, `*.example.com`) — Technitium
  wertet die in Allow-Lists nicht aus, sie wuerden nur stumm nichts tun.
* Alles, was nicht als Domain parst.
* Alles aus `quarantine.txt`.

Das Adblock-Format (`@@||example.com^`) und hosts-Format (`0.0.0.0 example.com`)
werden erkannt und auf die nackte Domain reduziert.

## Warum es eine Quarantaene gibt

Die Upstream-Whitelists sind fuer Leute gebaut, die sehr aggressive Blocklisten
fahren (Hagezi *Ultimate*), und geben dafuer Dinge frei, die man sonst gerade
blocken will — Ad Exchanges (AppNexus, Smart AdServer, Meta Ads/Pixel), Audience
Measurement (Nielsen, Conviva, Optimizely), Marketing-Automation (Braze, Drift,
Intercom), Windows-Telemetrie (`*.events.data.microsoft.com`,
`settings*.data.microsoft.com`) und die MSN-Werbeflaechen von Windows Spotlight.

Von 498 zusammengefuehrten Domains landen deshalb 49 in der Quarantaene, 449
bleiben. Wer *Pro* statt *Ultimate* faehrt, braucht diese 49 ohnehin nicht — sie
heben nur Blocks auf, die bei Pro gar nicht erst gesetzt werden.

Eine Allowlist ist die gefaehrlichste Datei im ganzen Filter-Setup: sie hebt Blocks
*still* auf. Man merkt nie, dass etwas durchgeht. Darum landen diese Eintraege in
`quarantine.txt` statt einfach mitgeschleift zu werden.

Brauchst du einen davon doch: Zeile aus `quarantine.txt` entfernen **und** mit Grund
und Datum in `allowlist-local.txt` dokumentieren.

## Hinweis fuer Kundenumgebungen

Vor dem Ausrollen die Domains von Branchensoftware samt Update- und Lizenzservern
explizit in `allowlist-local.txt` eintragen. Ein DNS-Block auf einen Lizenzserver
faellt oft erst Tage spaeter auf.
