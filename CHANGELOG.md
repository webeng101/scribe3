[size=22][b]This is version 4.0[/b][/size] ([u][ref=https://docs.google.com/document/d/1bsuel4sKqaF-Sg4Pf-OUUKg94ojjAM0_MQQBPUekW8A/edit?usp=sharing]Click here for the release notes[/ref][/u])
Essentially the same thing as 3.6, but running in python 3 behind the scenes.


[size=22][b][u]Past releases[/u] [/b][/size]


[size=22][b]Version 3.6[/b][/size] ([u][ref=https://docs.google.com/document/d/1RycWgX5sizUqaE_nU22kg8vuMOEmZeVgJU-2DilNz_U/edit?usp=sharing]Release notes[/ref][/u])

[size=16][b][i]Main changes[/b][/i][/size]
- Support scanning booklets of CD items
- Exit confirmation popup
- Help center
- C2 Widget
- Telemetry improvements
- Fix zero volume bug


[size=22][b]Version 3.5[/b][/size] ([u][ref=https://docs.google.com/document/d/1SNaix0Ifeh0ps6G59liB1HcXWD9EPXt4_S2wDWg0Sl0/edit?usp=sharing]Release notes[/ref][/u])

[size=16][b][i]Main changes[/b][/i][/size]
- RCS widget
- CLI improvements


[size=22][b]Version 3.3-3.4[/b][/size] ([u][ref=https://docs.google.com/document/d/17rlT4atRp-yn_MQ93vXD1d6mtK45mvu04-JuJhpLxos/edit#]Release notes[/ref][/u])

[size=16][b][i]Main changes[/b][/i][/size]
- Interactive MARC search
- Update manager
- Tooltips!
- Notifications improvements
- “Actions” framework
- Remote APIs (web and C2)


[u][size=18][b]Version 3.2[/b][/size] ([ref=https://docs.google.com/document/d/1C7Y24RxtSreuM1GDPekJnQm3WSQY-2-BvmiELgUXkXw/edit#]Release notes[/ref])[/u]

[size=16][b][i]Main changes[/b][/i][/size]
- User login front and center, automatic logout
- Notification center
- Support for contact switches
- Import book


[u][size=18][b]Version 3.1[/b][/size] ([ref=https://docs.google.com/document/d/12Sgwp_FO4UiW84-PUg2bH8yeKs0qVrVB6rXKvI9h47E/edit#]Release notes[/ref])[/u]

[size=16][b][i]Main changes[/b][/i][/size]
- [b]New camera system[/b]: no need to restart the app if cameras disconnect
- [b]New task system[/b]: see and control everything that the app is doing
- [b]Metrics[/b]: measure all the things and see stats about it
- [b]Mass digitization[/b]: rejection tracking, multi-catalog support

[size=16][b][i]Other changes[/b][/i][/size]
- [b]Info panel popup[/b] Open with T (right) or CTRL+T (left); defaults to focus on number field; use 9 to assert tissue
- Daemon mode
- Boxid validation is now 9 characters only
- Suppressed check for imagecount before deletion (would cause foldout stations not to delete received books)
- Removed old DWWI widget
- Improved messages in various popups (send to foldout, cookie, etc)
- Import feature (still disabled)
- Update internetarchive library to v 1.8.5
- No longer use “operator” from metadata.xml

[size=16][b][i]Bugs fixed[/b][/i][/size]
- Removing the last remaining page assertion (green bubble) wouldn’t display that it had correctly done so in the UI, leading the user to erroneously think that the page was still asserted
- Exit cleanly in case of two instances running
- Headers and column
- Entries were swapped between leafs and pages in rescribe screen
- Create correctly btserver item upon finishing setup


[u][size=18][b]Version 3.0[/b][/size] ([ref=https://docs.google.com/document/d/12Sgwp_FO4UiW84-PUg2bH8yeKs0qVrVB6rXKvI9h47E/edit#heading=h.i1bhub1txism]Release notes[/ref])[/u]
This version it is not backwards compatible and requires a 64 bits system to run. Besides this important change, 3.0 continues the evolution began with 2.1, away from the single-worker model of the 1.x series, and introduces a more sophisticated task execution runtime, more UI cues, better error handling and messaging. Some of these tasks are used to print slips, a key step in the mass digitization process: 3.0 also lets you have finer control over the slip printing process, and supports new scenarios and interactions. We have also tweaked the book lifecycle to better align with the processes used in both IA scancenters and mass digitization supercenters, and to deal with some typical cluster failure cases, as well as fixing bugs and improving the UI according to user feedback.

[size=16][b][i]Other changes[/b][/i][/size]
- Removed dependency on www-judec
- Put a “send to scribe” file in the item when sending foldouts to another station
- No longer uses “identifier” in scribe_config.yml
- Fixed a bug where loading preloaded items only loaded the metadata but not the identifier


[u][size=18][b]Version 2.1[/b][/size] ([ref=https://docs.google.com/document/d/1NCgAlmxRdgfVF6Fkp2YllxbH59cSt03iRgtdrXD8aaQ/edit]Release notes[/ref])[/u]
- Biggest leap in Scribe3 yet: task-based event-driven UI, entirely new backend, no more worker
- New features: Command Line Interface, Blur detection


[u][size=18][b]Version 1.64[/b][/size] ([ref=https://docs.google.com/document/d/1DAm9fvFj0PxYHD9lb72eAKUmkUCorYHvZ4tzYmS2QEA/edit]Release notes[/ref])[/u]

[size=16][b][i]Main changes[/b][/i][/size]
- Wonderfetch changes to support trent workflow
- Create an item when printing a slip, and upload the slip to the item
- New rules for what is “insufficient metadata”
- Smaller application package with the removal of an old, no longer in-use driver

[size=16][b][i]Bugfixes and other improvements[/b][/i][/size]
- QR code in reject slip would contain extra characters
- An empty response from IA during marc retrieval now doesn’t crash the app


[u][size=18][b]Version 1.63[/b][/size] ([ref=https://docs.google.com/document/d/10Nlu0iSjZPv3nsTDkQJpd6w0PhzCQd1u90nerKrdcc8/edit]Release notes[/ref])[/u]

[size=16][b][i]Main changes[/b][/i][/size]
- All book states use the new Book Info Panel
- Wonderfetch: Load metadata via OpenLibrary (limited to trent catalog for now), support string filtering via regex
- Title preset in add MD field
- Slips now have old_pallet qr code

[u][size=18][b]Version 1.62[/b][/size] ([ref=https://docs.google.com/document/d/1nQEnix6XZPY-1eMTXVvevLOeoyDHogrwK2oOdnu8Y9A/edit]Release notes[/ref])[/u]

[size=16][b][i]Main changes[/b][/i][/size]
- [b]Better​ UTF-8 handling in metadata ​​fields[/b] (enforce and automatically convert to ascii unicode md keys in compliance with IA md policy).
- Introducing a​ [b]new window component ​​to interact with books[/b] from the library list: see cover, key metadata and status at a glance, while maintaining the same buttons and workflows. The rollout will be partial so for this release, we’ll have some of the old interaction windows live next to this new one, which is available for statuses: Scribing, Upload Queued, Packaging Failed, all non-error corrections/foldouts states and Done. One of the main features of this window is ​help messages​​, which are meant to help you, the user, better understand what the status of a book is. They can be comments about the status of a book, or the reason for a failure.
- [b]Log view​​[/b]: for lovers only, click on Show log in the interaction window to reveal the output from the last time the worker did something to the book. Useful to understand what’s going on when things go very wrong.
- If you’re trying to create a book with [b]insufficient metadata​​[/b], the app will try and let you know.
- [b]More ​metrics​​[/b]: we now track camera performance in real time, acceptance yield for supercenters, and more error conditions. You will not see any of this quite yet, but we laid the foundations for having better stats.
- [b]Bugfixes[/b] here and there (more resilience in failure-prone web requests, issues removing books from lists in corrections, better boxid validation, more icons where possible).
- The [b]worker sleeping time has been decreased[/b] from 60 seconds to 10. This will make the app snappier.



[size=22][b][u]Legacy releases[/u] [/b][/size]

[size=18][b][u]Version 1.58[/u] [/b][/size]

[size=16][b][i]New features[/b][/i][/size]
[b]Opportunistic calibration[/b] Scribe3 now knows when it needs to calibrate cameras and will ask the user if it wants to do so. In all other instances, scanning can proceed without calibration. 
[b]Reset book button[/b]
[b]"Upload" & "upload + new" buttons[/b] now split and do the right thing in all situations (normal scanning, corrections, foldouts)
[b]Default collection set[/b]
[b]Showing popup to exit CaptureScreen[/b] if book is opened in 2+ cameras mode and is folio book.
[b]Camera times[/b] in scandata
[b]Better logging[/b]
[b]New scandata-based page numbering backend[/b]
[b]Ensure valid book metadata[/b] is saved when book is opened
[b]Keep the leaf metadata[/b] on spread reshoot
[b]Stripping of "Orientation"[/b] exif tag
[b]"ISBN" and "ISBN"[/b] as proper multi-entry metadata field(ensure values are semicolon separated!)


[size=16][b][i]Bugfixes and other improvements[/b][/i][/size]
[b]Solves a problem where temporary cluster errors may make a corrections book prematurely transition to a done state
[b]configurable identifier_reserved deletion policy
[b]Ignore entirely no change to _meta.xml errors
[b]Rotation bug for foldout station
[b]Allow adding camera value to pre-loaded items
[b]block any upload if the item has pending catalog tasks
[b]allow user to delete identifier_reserved books through popup
[b]option to set no-index by default in settings
[b]Ensure FFS->FOS color correction is turned off by default
[b]PageType popup disabling keyboard shortcuts
[b]Delete or insert spread causing crashes
[b]Crashes due to attempts to set PPI to 0
[b]Errors in displaying images upon opening a book
[b]PageType widget would show the wrong value for page number assertion under certain circumstance
[b]Fix a bug where a function was called incorrectly, causing deletion of identifier_reserved books to fail
[b]Corrections items would not display any notes
[b]Fixed a bug that would make it impossible to re-shoot a page after a camera failure, in some cases.
[b]PageType widget would show the wrong value for page number assertion under certain circumstances.

[size=18][b][u]Version 1.57[/u] [/b][/size] (2017-12-04)
Scribe3 1.57 introduces the scribe-to-scribe foldout workflow, color correction for FFS-FOS, improvements to Do We Want It and bugfixes.

[size=16][b][i]New features and bugfixes[/b][/i][/size]

[b]Foldouts workflow[/b] - Send books directly to a foldout station from inside Scribe3! Plus a ton of improvements; one above all? Open the book to the first foldout!
 
[b]Color Correction[/b] - To support foldout workflow, enable this option on your Full Frame Scribe and get more consistent imaging across platforms.

[b]Opportunistic calibration[/b] - No need to calibrate every time you scan a book any more!

[b]DWWI[/b] - Call DWWI directly from the main screen, automatically create identifiers upon loading items 

[b]Shiptracking ID[/b] - Now a column in library list, and visible inside Re-shoots index as well (also claimer!) 




[size=18][b][u]Version 1.56[/u] [/b][/size] (2017-11-17)
Scribe3 1.56 fixes all existing outstanding bugs with free-form foldout insertions and the final version of the new Re-shoots screen

[size=16][b][i]New features and bugfixes[/b][/i][/size]

[b]Re-shoots UI[/b] - Advanced features: skip between corrections, completion detector, start at next correction, upload from Re-shoots screen

[b]Logging[/b] - More aggressive logging (may create large files in your [i]~/.kivy/logs[/i] directory)

[b]Scandata[/b] - Now fully working in corrections insert mode (lots of bugfixes)




[size=18][b][u]Version 1.55[/u] [/b][/size] (2017-11-03)
Scribe3 1.55 introduces a first round of improvements to the Re-shoots screen, as well as numerous across-the-board improvements

[size=16][b][i]New features and bugfixes[/b][/i][/size]

[b]Re-shoots UI[/b] - Keyboard actions, specify page type, removed useless elements, harmonized UI consistency

[b]Telemetry[/b] - More aggressive reporting to iabdash

[b]Bugfixes[/b] - Handle a number of problem situations highlighted from Hong Kong 




[size=18][b][u]Version 1.54[/u] [/b][/size] (2017-10-06)
Scribe3 1.54 introduces a new UI for corrections (both list and re-shoots), as well as many bugfixes to support FOS.

[size=16][b][i]New features[/b][/i][/size]

[b]Re-shoots index[/b] - Revamped design, now making it easier and more accessible to select corrections, view the status of a reshooting at a glance, as well as richer metadata.

[b]Re-shoot UI[/b] - Cleaner design, jump between corrections, see richer metadata 

[b]Corrections Proxies[/b] - Download proxies generated on-the-fly. 

[b]Process[/b] - Refuse to scan preloaded items that are in anything but -1 repub_state 

[size=16][b][i]Fixes[/b][/i][/size]

[b]DWWI[/b] - When loading MARC metadata for a book we want, no longer crash.

[b]Scandata[/b] - Many improvements geared mostly towards guaranteeing correctness of scandata while allowing for inserts in most configurations.

[b]Offline mode[/b] - No longer hang when IABDASH is not available, no longer crash when loading an identifier offline.

[b]Upload errors[/b] - In case MD API returns an error, log the message.




[size=18][b][u]Version 1.53[/u] [/b][/size] (2017-10-06)
Scribe3 1.53 introduces the foldout skipping feature and many bug fixes to 1.52, especially geared towards FOS.

[size=16][b][i]New features[/b][/i][/size]

[b]Library list[/b] - Sort and search are supported, as well as a cover view.

[b]Re-shoots display[/b] - See preview of book cover, removed unnecessary buttons, cleaned up UI.

[b]Foldout skipper[/b] - When opening a book with foldouts (typically for FOS reshooting), see them marked on the slider and skip between them with the [b]f[/b] and [b]g[/b] keys, or by clicking on the buttons in the top bar, or just by clicking the markers. 

[size=16][b][i]Fixes[/b][/i][/size]

Various FOS fixes including corrections download preview and preview expansion on cluster (will be phased out)




[size=18][b][u]Version 1.52 [/u][/b][/size]
Scribe3 1.52 introduces Autopilot, improves the library view and a number of small, useful features. 

[size=16][b][i]New features[/b][/i][/size]

[b]Autopilot[/b] - Enable this feature to let Scribe3 set your camera configuration automatically.

[b]Library list[/b] - Improved UI controls with tooltips, added leaf count, right-click on the identifier to copy into clipboard.

[b]Shooting interface[/b] - Added assert-leaf-button in cover shot 

[b]Status bar[/b] - Now showing camera status at a glance at all times.
 
[b]Toast notification[/b] - You'll get a notification when a book is done downloading for corrections.

[b]Full screen[/b] - Press F11 to full-screen the app.

[b]FOS improvements[/b] - Automatically set source=folio for FOS items, enumerate foldouts correctly.

[b]Other [/b] - Faster email validation in 'operator' field, added a 'Cancel' button in foldout mode when shooting foldouts.

[b]Mark beginning of scanning[/b] - Set repub_state to -2 upon loading an IA identifier (either natively or through ISBN).

[b]Logging[/b] - Books now upload a log of their scanning, and terminal output has been improved further (especially upload)

[b]Telemetry[/b] - Now keeping track of file sizes and upload time to iabdash. 

[size=16][b][i]Fixes[/b][/i][/size]

Unpredictable failures uploading, loupe in scanning mode wouldn't refresh with new images, download from cluster would be botched
 
 
 

[size=18][b][u]Version 1.51[/u][/b][/size]

Scribe3 1.51 introduces a new Library, has better support for Do We Want It and FADGI

[size=16][b][i]New features[/b][/i][/size]

[b]Library list[/b] - Sort and search are supported, as well as a cover view.

[b]FADGI toggles[/b] - Turn on or off selected post-processing options: tone color correction, skip contrast enhancement, attach ICC profile

[b]Do we want it[/b] - Scribe3 now automatically fetches MARC records and metadata, where available, for books we want.

[b]Scanlogs[/b] - Books now contain a log of the scanning activities performed on them.

[b]Sticky operator[/b] - Operator field is now attached to the book at scanning time, not at upload time.




[size=18][b][u]Version 1.50[/u][/b][/size]

Scribe3 1.50, though very similar on the surface to previous versions, uses an entirely restructured backend and modern, updated libraries.

[size=16][b][i]New features[/b][/i][/size]

[b]Kivy 1.10 + SDL2[/b] - The app should be faster, snappier and crisper to display.

[b]Human-readable statuses[/b] - Library list now displays pretty status names.

[b]Books download[/b] - Support retries and timeouts (worker won't crash if connectivity is bad)

[b]Scribe3 version[/b] - Now pushed by default to all uploaded items.

[b]Collections[/b] - Fixed a longstanding bug that would cause incorrect handling of collections metadata in preloaded items.




[size=18][b][u]Version 1.40[/u][/b][/size]

Scribe3 1.40 introduces Single-camera mode, or the ability to scan foldouts, fully integrated in the corrections workflow.

[size=16][b][i]New features[/b][/i][/size]

[b]Foldout support[/b] - Use Scribe3 to scan books (or correct them) with just one camera.

[b]Insert[/b] - supported in single and multi-camera, on native and downloaded books, with or without assertions.

[b]Notes[/b] - Add notes to book as they are scanned, so that RePublishers will see them.

[b]Key bindings[/b] - are the same as in RePublisher.

[b]DWWI[/b] - Option in settings to disable donation items.

[b]PPI[/b] - Set per-image, per-book and per-machine PPI values.

[b]Corrections[/b] - Support for cluster changes, botched download recovery and better logging.

[b]origin.txt[/b] - No longer uploading

[b]Proxies[/b] - New option to use low-resolution proxies for faster scanning




[size=18][b][u]Version 1.30[/u][/b][/size]

Scribe3 1.30 introduces a significant UI refresh. While maintaining the field-tested book scanning workflow intact, this update introduces changes to four main areas: the app frame, the library list, the scanning UI and the settings, as well as adding a number of functional features.

[size=16][b][i]New features[/b][/i][/size]

[b]Top bar[/b] - where navigation through app screens happens, including a consolidated "back to home" button that replaces multiple controls that used to exist in disparate places in the app. On the right-hand side, a dropdown menu is available to navigate into the settings (in place of the simple gear icon); this menu show the currently logged-in user, as well as the scanner name. 

[b]Book bar[/b] - in scanning screen allows for direct edit of books' metadata, as well as quick actions.

[b]Leaf bar[/b] - Allows quick access to actions (import, export, see original) per every leaf, including calibration

[b]Book bar[/b] - Allows you to navigate inside a book and displays information when you hove on the knob: [current spread][total # spreads] | [leaf left][leaf right] | [asserted_left][asserted_right]

[b]Autoshoot timer[/b] allows for automatic picture-taking after a configurable timeout (default 4 seconds). Use with caution as it may overload the camera bus and result in overall slowness.

[b]MARC records & MARC catalogs[/b] - In the book metadata view, this system allows for querying partners' catalogs via IA's z39.50 connections and add MARCXML and MARC binaries to the item being scanned. Before doing this, please remember to set up your catalogs in the "Catalogs" settings tab.

[b]Do We Want It?[/b] This feature is designed specifically for IA internal scanning centers, and allows the user to evaluate a book (by scanning or typing its isbn) and check on IA whether we actually need to scan it or not. Actions and workflows are supported for boxing where necessary. The wizards can be accessed from library list, as well as from a book's cover view.

[b]Library list[/b] - now highlights selected books, presents more and better options interaction options and displays book identifier where present

[b]Key bindings[/b] - use the keyboard to trigger key actions like shoot, reshoot, autoshoot, delete, assert leaf. You can customize these via the ~/.scribe/capture_action_bindings.json. This feature allows you to scan an entire book without ever touching the mouse.

[b]Refreshed settings[/b] - now less crash-prone and improved, settings have been revamped and new tabs and controls added.

[b]"About your scribe"[/b] - info panel shows an overview of your metadata, camera status, books, etc at a glance

[b]Use TAB[/b] to cycle through text boxes

[b]Tooltips[/b] - new and old UI components now have tooltips 

[b]Preloaded items in offline mode[/b] - Scribe3 now allows you to load a preloaded item even when IA is not reachable and verifies later that the identifier and metadata are correct, letting you correct it in case of error.

[b]Exif tags in JP2[/b] - If exiftool is installed on the system, Scribe3 will copy EXIF data from the source jpgs to the JP2s in preimage.zip. If Exiftool is not available, a banner will be displayed in settings

[b]Import[/b] a jpg image as a leaf

[b]Export[/b] - now every picture taken by Scribe3, including the calibration images, can be seen in original and exported. 

[b]Native file chooser[/b] - Use ubuntu's default file chooser for import/export functionalities, resulting in a much faster and consistent user experience.

[b]UTF-8 support[/b] - The ui now fully supports other character sets like thai or chinese (UTF-8)

[b]Collection settings toggle[/b] - Enable this in settings to access the collections set editor, without having to go through the wizard again

[size=16][b][i]Improvements[/b][/i][/size]

- New unified back button consistenly located on top bar

- Dismiss scan cover popup with ENTER or ESC

- Logging is improved and unnecessary data dumps have mostly been removed from the Scribe3 execution log.

- Tidier, friendlier camera logs in the format: [unix timestamp], [side], [port], [angle], [camera time], [thumbs time], [path], [thread]

- Page assertions: Assert any page as foldout, and assert any foldout page (shot with LIC) as any page type.

- Rejected corrections now handled. 

[size=16][b][i]Fixes[/b][/i][/size]

- Spinners are back!

- Correct handling of the 'creator' field

[size=14][b][i]Upgrade notes[/b][/i][/size]

This version does not require significant input from the user and should work out of the box upon update. Please not that it does make some breaking changes to the settings file, which may no longer be readable by previous version, was the user to downgrade (this issue can be addressed by deleting the file)




[size=18][b][u]Version 1.22[/u][/b][/size]

[size=16][b][i]New features[/b][/i][/size]

- [b]Camera shoot sound[/b] - Scribe3 now produce a shoot sound upon pressing the "SHOOT" button.

  The delay can be controlled by the non-UI facing setting "sound_delay" in camera_setting.yml like so:
      camera_shoot = [time in milliseconds]

      for example

      sound_delay = 0.5

  A default value of 0.1 is assumed if this value is not present. To turn off the feature, set

      sound_delay = -1

  In order for this feature to work, speakers are necessary. 

[size=16][b][i]Fixes[/b][/i][/size]

- [b]Non-blocking corrections download[/b]

    In versions up to 1.22, corrections would download on app startup, blocking execution until finish. In this version
    corrections download in the background - though in the same thread. As a result, the user will not see the books in the
    list until they are downloaded (which may take a while).

    This change doesn't require user interaction to work.

[size=16][b][i]Updates[/b][/i][/size]

- All Sony cameras now use Gphoto v.2.5.10

[size=14][b][i]Upgrade notes[/b][/i][/size]

    
Required items:
    - SPEAKERS: This version requires speakers (embedded in the HDMI monitor for stations issued in 2017 or external if older).
    - Internet connection

Update as usual by clicking on the "update" button
