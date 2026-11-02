# Spike S3 findings: hosting and the browser

Task P0-T6. Architecture sections 9.2, 9.3 and 12.4. Done on 2 November 2026. Decided by discussion point 102, recorded in architecture AD-9 and requirement PCK-4.

## The questions

* Can the web version read a pack straight from GitHub Releases, one record at a time, with range requests from its worker?
* If not, which other place works: Hugging Face, then Cloudflare Pages?
* How much can a browser keep in its private storage, in Firefox, Chrome and Edge?

The words used here, such as range request, web permission and private storage, are in the glossary.

## Short answer

* GitHub Releases does not work for the web version. Chrome, Firefox and Edge all block a web page from reading a file there, because GitHub's download server does not send the web permission. The desktop version is not affected.
* Hugging Face works in all three browsers. Range requests return exactly the bytes asked for, and the browser lets the page read them.
* But each read from Hugging Face takes about a third to half a second, from this laptop. That is too slow to read records one at a time while stepping, where the target is 150 milliseconds (NFR-1).
* Downloading a whole file from Hugging Face is quick: about 32 megabytes a second here. The 38 MB S2 stage 1 pack would take a little over a second.
* Private storage works in all three browsers, with the same kind of worker access the pack reader will use. Each browser reported a storage limit of 10 GB for the site. Firefox stopped writing at 10 GB. Chrome and Edge wrote 12 GB without complaint. Your own Firefox gave the same 10 GB, and you could allow kept storage with NVDA without trouble.
* Recommendation (DP102): keep the packs on GitHub Releases for the desktop, with a copy on a Hugging Face dataset for the web. The web version downloads each pack whole into private storage, rather than reading it one record at a time, and reads records from there. While a pack downloads, it can use range requests to show the map straight away.

## Nothing was published

* On 2 November you chose not to publish a test file to the TobyMap repository, and not to set up a Hugging Face dataset yet.
* So the internet tests used files that other projects have already published:
  * GitHub Releases: a 5.6 MB file in the Pyodide project's release 0.27.0. It is served by the same GitHub download server that TobyMap's releases would use.
  * Hugging Face: a 0.4 MB file in the public GSM8K dataset, and a 2 GB file in the public FineWeb dataset for the download speed.
* The tests on this computer used TobyMap's own 64 MB test file, with a known pattern, so every byte read was checked.
* TobyMap's own Hugging Face dataset is set up in Phase 1, when packs are first published.

## How it was tested

The spike is in tools\spikes\s3:

* A test page, with a worker that makes synchronous range requests, as the web version's pack reader will (architecture 4.4).
* Three servers on this computer: the test page; the test file with the web permission; and the test file without it, behaving as GitHub's download server does. So the blocking is shown, and tested in continuous integration, with no internet.
* A runner, run.py, which opens the page in Chromium, Firefox and Edge without a window, runs every test, and saves the results in docs\spikes\s3-results.

For each place, the reading test:

1. reads the first 16 bytes, which shows whether the browser allows it at all;
2. makes 20 reads of 4 KB from all over the file, as when stepping round the map, and times them;
3. reads the last 16 bytes;
4. makes one read of up to 4 MB, for the download speed;
5. keeps what the 20 reads returned in private storage, reads it back and checks it, as the pack cache will do.

The storage test writes a test file into private storage, 16 MB at a time, until it reaches the amount asked for or the browser stops it. It then reads some of it back, checks it, and deletes it.

## Results: reading

The browsers were Chrome 156, Firefox 157 and Edge 156.

### This computer, with the web permission

* Works in all three browsers.
* Every byte checked correct.
* Each 4 KB read took about 5 to 22 milliseconds.

### This computer, without the web permission

* Blocked in all three browsers, as expected.
* Chrome and Edge report a network error. Firefox reports nothing at all: the read just comes back empty, with status 0. The pack reader must treat both as blocked.

### GitHub Releases

* Blocked in all three browsers.
* GitHub's own address sends the browser on to its download server, release-assets.githubusercontent.com. Neither sends the web permission.
* The download server does answer range requests correctly. That is what the desktop needs: a 4 KB read took between 0.1 and 0.3 seconds, and 4 MB downloaded at about 19 megabytes a second.

### Hugging Face

* Works in all three browsers.
* Hugging Face's own address sends the web permission and sends the browser on to its download server, us.aws.cdn.hf.co, which sends the web permission too.
* Each 4 KB read took about 0.35 seconds in the middle, and up to 0.7 seconds at slowest. Reading the same range twice was no faster.
* The time is mostly waiting, not downloading:
  * Hugging Face's own address takes about 0.14 seconds to send the browser on.
  * The download server then takes about 0.3 seconds, even for 4 KB.
* A 32 MB read took about 1 second, about 32 megabytes a second.
* What came back was always the right length, and the reads kept in private storage read back correctly.

### What this means

* The browsers' rules are as expected (architecture 9.2), so the web version cannot use GitHub Releases.
* Hugging Face works, but reading one record at a time from it would make a step take half a second wherever the record isn't already stored. So the web version should download a pack whole, or in large sections, and read records from private storage. Then steps are as fast as on the desktop.
* The 150 millisecond target (NFR-1) is for data that is installed. That fits: in the web version, installed means downloaded into private storage.
* PCK-4 asks this spike whether GitHub release downloads can serve ranges of a file. They can, so the desktop can read packs from GitHub Releases on demand (PCK-3). The web version cannot, because of the missing web permission, so for the web the design needs another place. That is DP102.
* PCK-3 asks for a detailed announcement within 3 seconds when moving into an area that isn't installed. A lookup reads the pack's directory, then at most one pack tile at each tile level, one after another. At about 0.4 seconds a read from Hugging Face, that is likely to be close to 3 seconds in the web version, and well within it on the desktop from GitHub. Reading neighbouring pack tiles in one larger range request would help. It is measured in Phase 1.

## Results: private storage

### What each browser allowed

* All three reported a storage limit of 10 GB for the site, with nothing yet stored.
* Firefox stopped writing at 10,224 MB, just under the limit, with no error.
* Chrome and Edge wrote 12 GB, beyond the limit they reported, without stopping.
* Writing was fast in all three: between 800 and 1,100 megabytes a second.
* Everything read back correctly, and deleting the test file gave the space back.
* None of the three had kept storage for the site. So a browser could clear the packs when the disk gets full, unless TobyMap asks for kept storage.

### What this means

* 10 GB is far more than the 250 MB base pack (PCK-1), and enough for several 1 GB packs.
* These runs used new browser profiles with no window. Your own Firefox may report a different limit, so the pack manager should always ask the browser how much is left (architecture 9.3), not assume 10 GB.
* TobyMap should ask for kept storage when you first install a pack beyond the base pack. Firefox shows a prompt for this, and you could use it with NVDA.

## The other places

* Cloudflare Pages: not tested. It is only needed if Hugging Face fails, and it would need a TobyMap site set up there first. Each file is limited to 25 MB, so packs would have to be split.
* GitHub Pages: it does send the web permission, checked on 2 November. But each file must be under 100 MB and the whole site under 1 GB, so at most it could hold the base pack. It is not needed while Hugging Face works.
* GitHub's raw file server and jsDelivr also send the web permission, but they serve files in the repository itself. Packs are never committed (CLAUDE.md rule 10), so they are not suitable.

## Results from the automatic checks

* 14 Python tests check the test file's pattern and how the server reads range requests.
* 2 browser tests, in Chromium and Firefox, run the page against the servers on this computer:
  * reading works with the web permission and is blocked without it, every byte checks correct, and the cache round trip works;
  * the storage test writes 32 MB, reads it back and cleans up.

## Your test in your own Firefox, 2 November

You ran the page in your own Firefox, version 159, with NVDA. The results are in docs\spikes\s3-results\2026-11-02-1015-firefox-po.txt.

* Reading: the same as the automatic runs. GitHub Releases was blocked, and Hugging Face worked, at about 0.35 seconds a read.
* Storage: Firefox reported a 10 GB limit and stopped writing at 10,224 MB, the same as in the new test profiles. Writing ran at about 1,100 megabytes a second, everything read back correctly, and the test file was deleted.
* Kept storage: Firefox's prompt appeared, and you could reach its Allow button with NVDA without trouble. Firefox then agreed to keep the site's storage.

So asking for kept storage is usable with NVDA in Firefox, and the 10 GB limit holds in a real profile.

You can try the storage test again in Firefox if you like, as the limit may now be higher because the site's storage is kept. It is not needed for the decision.

To run the page yourself in Firefox again:

1. In PowerShell, in the repository folder, run: `.venv\Scripts\python.exe tools\spikes\s3\run.py --serve`
2. Open the address it prints in Firefox.
3. Use the buttons, then press Ctrl+C in the PowerShell window to stop.

## Decision

You accepted the recommendation on 2 November (DP102). It is recorded in architecture AD-9 and sections 9.1 to 9.3, and in requirement PCK-4:

* Packs stay on GitHub Releases for the desktop.
* The pipeline also publishes each pack to a TobyMap dataset on your Hugging Face account, for the web version.
* The web version downloads each pack whole into private storage and reads records from there. While a pack is downloading, it uses range requests.
* When you install your first pack beyond the base pack, the web version asks the browser to keep its storage.

## Left for later

* Phase 1: set up TobyMap's Hugging Face dataset, publish the first pack to it from the pipeline, and time a whole download from there.
* Phase 1: the web pack reader, which downloads packs into private storage and uses range requests only while a pack is downloading.
* Spike S4 (P0-T7): Pyodide reading the S2 pack in the web version. It can read the pack from private storage, as this spike recommends.
