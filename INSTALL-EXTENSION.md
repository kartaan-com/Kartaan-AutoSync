# Installing the Kartaan Auto-sync extension

Kartaan Auto-sync is not on the Chrome Web Store. Sellers install it from a ZIP file.

## For a seller

1. Download the ZIP: https://github.com/kartaan-com/Kartaan-AutoSync/releases/latest/download/kartaan-autosync-extension.zip
2. Unzip it into a folder you will keep, such as `Documents\Kartaan Auto-sync`. Not Downloads: Chrome
   reads the extension from that folder every time it starts, so deleting the folder removes it.
3. In Chrome open `chrome://extensions`, switch **Developer mode** on (top right), press **Load
   unpacked**, and choose the folder that holds `manifest.json`.
4. The extension card appears. It may use Meesho, Flipkart, Amazon Seller Central and Google (for your
   Drive). Chrome asks nothing when you load it this way.
5. To update: download the ZIP again, unzip over the same folder, and press the reload arrow on the
   extension's card in `chrome://extensions`. If Chrome shows a new permission, accept it or the
   extension stays off.

## The extension's number is the same for everyone

The manifest carries a public key, so Chrome gives the extension this number on every machine:
`hkmghdnmbnfhaeblmfhpjlkcifpodbdo`. The ERP and the Google sign-in are told that number. The
matching private key is not in any repository; the owner keeps it on his own computer (file
`autosync-extension.pem`), and it is needed only to sign a package later, never to install. **Back it up.**
Replacing the key changes the number and breaks every sign-in until the step below is repeated.

## The owner's one step in Google (to do by hand, once)

The extension signs in to Google with the client named `kartaan-app` (Chrome Extension type,
`668375542231-8pr119f04gfe545h7jf2knuf8fl17spt`). It was set up with the number the folder used to
give, `nadhofphdfjgmphafkbfcodkncjpeigh`. Change it to the fixed one:

1. Open the Google API console, Clients page, signed in as the account that owns the project.
2. Open the client `kartaan-app` (Application type: Chrome Extension).
3. In the **Item ID** field, replace `nadhofphdfjgmphafkbfcodkncjpeigh` with
   `hkmghdnmbnfhaeblmfhpjlkcifpodbdo`.
4. Save. Google can take a few minutes to pass this on.
5. In Chrome, reload the extension, press **Connect Drive** in its panel, and check it says connected.

(Google's page for this: developer.chrome.com/docs/extensions/how-to/integrate/oauth.)

## Making the download appear (owner or Control)

Publish a GitHub release on `kartaan-com/Kartaan-AutoSync`. The workflow `extension-zip.yml` zips
the `extension` folder and attaches it as `kartaan-autosync-extension.zip`, so the link above works
from then on and always gives the newest release. Until the first release is published the link
returns "not found".

**Then tell installed copies a newer one is out -- LAST (A82).** `extension/manifest.json`'s `version` must be the release's version (0.1.17 for v0.1.17) before the release is made. Once the release and its ZIP exist, run `node tools/write_version.mjs "One line about what is new"`, then `git add version.json && git commit -m "Announce 0.1.17" && git push`. The panel reads `version.json` once a day and shows "A newer version is out" with the download link. Pushed before the release exists, it points sellers at a ZIP that is not there.
