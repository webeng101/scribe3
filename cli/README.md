# Scribe3 Command Line Interface

## Overview
The Scribe3 runtime is comprised of numerous services and components, 
which are usually interacted with through the various widgets of the GUI. 
This CLI offers an alternative way to do so with in a text-based mode. 

## Availability
On a Scribe3 station, the CLI can be accessed in one of two ways: 

1. By starting Scribe3 in *pure CLI mode*: you can do this by running
```
ia-scribe --mode cli
``` 

or, if you are running from code: 

```
python main.py --mode cli
``` 
2. Through the *CLI Widget*: by clicking the top bar dropdown and selecting `CLI Widget`

Functionally, the main difference between the two is that in the former mode no GUI is spawned, 
and the task system is essentially inactive. In pure CLI mode, the app only does 
what you tell it to. Please note that in this mode, `move_along` tasks are ran on the 
main thread.

In pure CLI mode, an auto-completion feature is present as well.

Additionally, the CLI is also the entry point for most of the the 
[Command and control](https://git.archive.org/ia-books/scribe3-server) API surface, 
though not all commands are available through the C2 (for example `notifications`, 
because `EventDispatcher` is not pickleable), and some C2 commands 
are not part of the CLI (for instance `screenshot`).

## Conventions
I will indicate CLI commands by prepending the `> ` symbol. This same is present as 
part of the the native REPL prompt (`Scribe3>`), but not in the widget version.
I will indicate the response from the CLI with the `%>` symbol, 
just like it happens in the REPL.

For example:
```
> command
%> response
```

## Syntax
The CLI makes use of space-separated words; the base syntax is as follows: 

```
> [command] [first arg] [second arg] ... [n arg]
```

The first word is always interpreted as the command, and every subsequent 
word is interpreted as an argument to that command. Commands may or may not take 
arguments, and may differ in how they interpret them.  

The CLI always returns pretty-printed dictionaries or lists. 

## Commands
The CLI is a thin wrapper over python objects. Essentially, it just lets you invoke
methods in those classes and in so doing, interact with their instances. 
This is done by passing an instance to a handler; when a command is received, it
is dispatched to the appropriate handler, which takes care of interpreting the 
arguments, evaluating and return the result.

When called without arguments, the CLI typically returns a list of methods of 
the commanded instance (if they don't begin with `_`).

Commands are defined in `ALLOWED_TOKENS`, in the `cli.py` file. This section presents
some notable ones. 

### `help`
This command will print a welcome message, and the list of available commands.

```
> help
%> {u'allowed_commands': [u'help',
                       u'print',
                       u'clear',
                       u'exit',
                       u'library',
                       u'book',
                       u'telemetry',
                       u'metadata',
                       u'rcs',
                       u'config',
                       u'move_along',
                       u'notifications',
                       u'cameras',
                       u'stats',
                       u'update',
                       u'restart'],
 u'message': u'This is the help function of Scribe3 CLI. Welcome!',
 u'usage': u'The book command takes a book class method name as second parameter and any subsequent argument will be passed to this downstream method.'}

```

### `library`
This command allows you to interact with the `Library` object, 
as defined in `ia_scribe/book/library.py`. The base syntax is as simple as 

```
> library [method] [arguments]
```

To get a list of available methods, you can just invoke the bare command:

```
> library [method] [arguments]
``` 

Listings of all books can be obtained as either a list, using the `list_all_books` command
```
> library list_all_books
Scribe3> library list_all_books                                                 
%> ['<acfe6a29-8869-48a9-bb08-ac62347507af is Scribing (scribing-200)>', 
    '<309bfb3d-43ea-4359-ac17-0f3aef7a1a9c is Scribing (scribing-200)>']
```
or as a dictionary, with the local uuid as key, with the `dict_all_books` method:
```
> library dict_all_books
Scribe3> library list_all_books                                                 
%>  {'6651848e-db06-4c24-b9ca-df80521cf77b': '<6651848e-db06-4c24-b9ca-df80521cf77b is Identifier assigned (identifier_assigned-300)| testidentifier12345>', 
     'cede4136-4581-4f7c-826f-e09439ffa1c0': '<cede4136-4581-4f7c-826f-e09439ffa1c0 is Scribing (scribing-200)>' }
```

If we want the books represented by something other than their `__repr__`, which 
defaults to showing uuid, status and IA identifier if present, both these methods
take a renderer: arguments after either `list_all_books` or `dict_all_books` will 
be interpreted as a method of the `Book` class, the return of which will be used
as a representation of the object. For example:

```
> library list_all_books name_human_readable                                                                                                                                                                                                                                                                                                               
%> ['acfe6a29-8869-48a9-bb08-ac62347507af', 
    '309bfb3d-43ea-4359-ac17-0f3aef7a1a9c', 
    'researchmethodsi0000roys', 
    '74a187c0-890d-492e-8f8c-afe15ce61891', 
    'adventuresofpino0000coll_e4y3']
``` 
if we wanted to get a list of UUIDs, and where present, identifier. 

In order to get slip metadata for books that have it, you could use:
```
>library dict_all_books get_slip_metadata                                                                                                                                                                                                                                                                                                                 
%> { 'f14f31c0-b7a4-47c3-9dc3-325f1f140701': None,
 'fc4efb84-a4c6-42b9-b35d-39ee919168e3': None,
 'fd448ca2-9aa1-4617-9c43-14ef557c5434': {u'datetime': u'20191022233618',
                                          u'identifier': u'buprenorphinealt0000unse',
                                          u'scanner': u'davide-dev.sanfrancisco.archive.org',
                                          u'timestamp': 1571787378.287471,
                                          u'type': 2},
 'feab757a-21b2-4219-bbb9-cd8d35074ab5': None,
 'ff54803a-362f-496e-a822-6098e14a9099': {u'comment': u'',
                                          u'datetime': u'20190923144656',
                                          u'isbn': u'0123456789',
                                          u'reason': u'Duplicate',
                                          u'scanner': u'davide-dev.sanfrancisco.archive.org',
                                          u'timestamp': 1569250016.814645,
                                          u'type': 3}}

``` 

In order to get any specific attribute of the book class, you can use the `get` method, 
followed by the name of the attribute, like so:

```
> library dict_all_books get status                                                                                                                                                                                                                                                                                                                        
%> {'6651848e-db06-4c24-b9ca-df80521cf77b': 'identifier_assigned', 
    'cede4136-4581-4f7c-826f-e09439ffa1c0': 'scribing', 
    '4bbf8a2c-0b99-4649-8a71-1cc3fd51d06e': 'uuid_assigned'}
```
or
```
> library dict_all_books get leafs   
%> {'6651848e-db06-4c24-b9ca-df80521cf77b': 2, 
    'cede4136-4581-4f7c-826f-e09439ffa1c0': 28, 
    '4bbf8a2c-0b99-4649-8a71-1cc3fd51d06e': 1539, 
    '3ba12b0d-f92d-48c6-9d56-0788993e23e8': 332, 
    'e6d2b631-8a4e-45da-8e2e-b37c674b602f': 751}
```
You can also filter books that match some criteria by using the `get_books` command, followed by the field you want to match
(in this case, `status`) and the value (`corrections_in_progress`):

```
> library get_books status corrections_in_progress                                                                                                                                                                                                                                                                                                         
%> ['<42574488-10fc-4330-bfbb-25146a0f79fc is Corrections in Progress (corrections_in_progress-825)| benezitdictionar09bene>', 
'<330ba230-699c-4651-afed-d2472afaac00 is Corrections in Progress (corrections_in_progress-825)| unset0000unse_g9i3>', 
'<894de6f2-f0cf-4003-a229-8bbb33f34777 is Corrections in Progress (corrections_in_progress-825)| godelescherbache0000hofs>']
```

This method also supports a renderer, for instance, to just get the UUID:

```
> library get_books status corrections_in_progress get uuid                                                                                                                                                                                                                                                                                                
%> ['42574488-10fc-4330-bfbb-25146a0f79fc', 
'330ba230-699c-4651-afed-d2472afaac00', 
'894de6f2-f0cf-4003-a229-8bbb33f34777']
```
You can also run state machine transitions en masse. For instance, 
if you wanted to move to trash all rejected books, we ask the library to list all the books 
in `status` `rejected`; we then exploit the renderer, which is just a method of the `Book`
class that is called for every instance, by asking it to run the `do_move_to_trash` method: 
```
>library get_books status rejected do_move_to_trash
```

### `book`
This command allows you to interact with a `Book` object, 
as defined in `ia_scribe/book/book.py`. As usual, typing the bare command will display a dictionary with information
about how to use the command, as well as a list of methods available to you.

```
> book                                                                                                                                                                                                                                                                              
%> {u'commands': [u'as_dict',
               u'get',
               u'get_available_methods',
                ...
               u'was_image_stack_processed_wrapper'],
 u'usage': u'book <uuid>'}
```

Unlike with `Library`, of which there
is only one, many `Book`s typically exist on a station; the command therefore 
expects the following syntax:

```
> book [uuid] [method]
```

Uuids are [RFC 4122](https://tools.ietf.org/html/rfc4122.html) version 4  128 bit-long strings.
UUIDS are never archive identifiers. Invoking the `book` command on a UUID without further arguments will cause
the CLI to call `as_dict`, which will return a dictionary representation of the book.

```
> book 1d8b043a-3b36-4145-b3f2-010c3b9ecc97                                                                                                                                                                                                                                                
%> {'boxid': '',
 'creator': None,
 'date': 1581027289.150212,
 'date_last_modified': 1576247770.631004,
 'date_created': 1576247770.631004,
 'error': None,
 'identifier': 'testidentifier12345',
 'leafs': 4,
 'msg': '',
 'notes_count': 0,
 'operator': u'davide@archive.org',
 'path': '/home/vagrant/scribe_books/1d8b043a-3b36-4145-b3f2-010c3b9ecc97',
 'shiptracking': '',
 'status': 490,
 'status_human_readable': 'Packaging complete',
 'title': None,
 'uuid': '1d8b043a-3b36-4145-b3f2-010c3b9ecc97',
 'volume': None,
 'worker_log': ''}
```
Once selected a book, you can use any method (as listed in the bare command listing). For instance:
```
> book 1d8b043a-3b36-4145-b3f2-010c3b9ecc97 get_status_history                                                                                                                                                                                                                             
%> ['Thu 2019 Dec 12 | 16:22:25 -> Identifier assigned',
 'Thu 2019 Dec 12 | 16:22:42 -> Packaging queued',
 'Thu 2019 Dec 12 | 16:22:42 -> Packaging started',
 'Thu 2019 Dec 12 | 16:22:42 -> Detecting blur',
 'Thu 2019 Dec 12 | 16:22:42 -> No blur found',
 'Thu 2019 Dec 12 | 16:22:42 -> Compressing images',
 'Thu 2019 Dec 12 | 22:09:18 -> Creating images bundle',
 'Thu 2019 Dec 12 | 22:09:18 -> Created images bundle',
 'Thu 2019 Dec 12 | 22:09:18 -> Packaging complete',]
```
As seen before in the library list example, the `get` method can be used to fetch any
particular field, for instance `boxid`:

```
> book fef5af86-ff9c-4875-b5b9-f98a3bd826fd get boxid                                                                                                                                                                                                                                      
%> u'IA1664906'
```

A special method that is available for your convenience is `get_available_methods`, which can be called 
on a book instance, and will display both the native `Book` methods, as well as the ones you can call to manipulate
the state of the book. These are available under the `state_machine` key. 
```
Scribe3> book 309bfb3d-43ea-4359-ac17-0f3aef7a1a9c get_available_methods                                                                                                                                                                                                                          
%> {'natural': ['as_dict',
             ...
             'is_downloaded',
             'is_locked',
             'is_modern_book',
             'is_preloaded',],
 'state_machine': ['can',
                   'cannot',
                   'current',
                   'do_begin_packaging',
                   'do_book_upload_begin',
                   'do_create_identifier',
                   'do_create_image_stack',
                   'do_create_metadata',
                    ...
                   'do_upload_book_anew',
                   'do_upload_book_done',
                   'do_upload_book_end',
                   'do_upload_book_error',
                   'do_upload_book_retry',
            ]}
```
For example, you may want to know if you can run a certain transition:
```
> book 309bfb3d-43ea-4359-ac17-0f3aef7a1a9c can do_book_upload_retry                                                                                                                                                                                                                       
%> False
> book 309bfb3d-43ea-4359-ac17-0f3aef7a1a9c can do_move_to_trash                                                                                                                                                                                                                           
%> True
```
You can also actually run that transition and move the book to trash.
```
> book 309bfb3d-43ea-4359-ac17-0f3aef7a1a9c do_move_to_trash                                                                                                                                                                                                                               
[2020-02-06 22:32:56,202][INFO ][MainThread][Book_309bfb3] State change: scribing -> trash
%> None
```

### `move_along`
This command allows you to run a the evaluator engine on a book. This is the component that decides what to 
do with a book once it's in a certain status. Moving a book a status doesn't do anything until the engine
is ran against it, at which point things (like creating a `preimage.zip`, uploading or deleting) actualy happen.

This command is fairly straightforward and takes only one argument, which is the book uuid:
```=
> move_along                                                                                                                                                                                                                                                                               
%> {u'usage': u'move_along <book uuid>'}
```
and when ran, it looks something like this (in this case, the book we moved to the trash earlier actually gets deleted):
```
> move_along 309bfb3d-43ea-4359-ac17-0f3aef7a1a9c                                                                                                                                                                                                                                          
[2020-02-06 22:49:39,204][INFO ][MainThread][Book_309bfb3] 
********************************
Book engine active at 20200206224939 on <309bfb3d-43ea-4359-ac17-0f3aef7a1a9c is Trash (trash-996)>
[2020-02-06 22:49:39,204][INFO ][MainThread][Book_309bfb3] move_along: Moving status if I can <309bfb3d-43ea-4359-ac17-0f3aef7a1a9c is Trash (trash-996)>
[2020-02-06 22:49:39,204][INFO ][MainThread][Book_309bfb3] move_along:: I can delete!
[2020-02-06 22:49:39,204][INFO ][MainThread][Book_309bfb3] Checking whether it is safe to delete this book
[2020-02-06 22:49:39,204][INFO ][MainThread][Book_309bfb3] Book was scanned on this station. Verifying with cluster...
[2020-02-06 22:49:39,221][INFO ][MainThread][Book_309bfb3] verify_uploaded: Verifying <309bfb3d-43ea-4359-ac17-0f3aef7a1a9c is Trash (trash-996)> was uploaded to the cluster.
[2020-02-06 22:49:39,222][INFO ][MainThread][Book_309bfb3] verify_uploaded: No identifier.txt. Assuming empty book and deleting.
[2020-02-06 22:49:39,222][INFO ][MainThread][Book_309bfb3] State change: trash -> deleted
[2020-02-06 22:49:39,223][INFO ][MainThread][Book_309bfb3] move_along: Done in 0.0192592144012 at 1581029379.22
********************************
```

### `config`
The `config` module lets you interact with the `Scribe3Configuration` service object, which is a file-backed key-value
store holding various aspects of Scribe3 in memory. 

```
> config                                                                                                                                                                                                                                                                          
%> {u'commands': [u'dump',
               u'get',
               u'get_integer',
               u'get_numeric_or_none',
               u'has_key',
               u'is_true',
               u'is_valid',
               u'set',]}
```  
The `dump` method allows you to see the full contents of the configuration:

```
> config dump                                                                                                                                                                                                                                                                              
%> {'auto_update': False,
 'camera_logging': False,
 'catalogs': {'marygrove': 'true', 'sfpl': 'true'},
 'check_for_update_interval': '1', 
...
```
To retrieve the value of a specific field, you can use `get`:
```
> config get move_along_at_startup                                                                                                                                                                                                                                                         
%> True
```
To set a different value, you can use `set`:
```
> config set move_along_at_startup false                                                                                                                                                                                                                                                   
%> None
> config get move_along_at_startup                                                                                                                                                                                                                                                         
%> 'false'
```
Please note the CLI only deals in strings, so here you are setting a boolean to a string. This will still work
because interally Scribe3 tends to use `is_true`, which knows to treat truthy strings as True and vice versa.

You can also read and write nested dictionaries by using the `/` symbol to separate keys:
```
> config set test/value1 one                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               
[2020-02-06 23:04:47,253][INFO ][MainThread][Saved configuration
> config get test                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               
%> {u'value1': u'one'}
> config get test/value1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          
%> u'one'
```

### `update`
This module allows you to interact with the update subsystem. It only makes sense to use this if you 
are running the packaged version of Scribe3 (i.e. not from code) and with a properly provisioned machine, otherwise
it will likely not work. As usual, the bare command tells us what sub-commands are available:

```
> update                                                                                                                                                                                                                                                                                   
%> {u'commands': [u'do_check_update',
               u'do_update',
               u'get_build_tag',
               u'get_update_channel',
               u'get_update_status',
               u'load_channel',
               u'schedule_update_check',]}
```
To get the current update status, as described in `ia_scribe.update.update.UpdateStatus`, simply run:
```
> update get_update_status
%> 'up_to_date'
```
Check for update (if auto-update is on and an update is available, this will also trigger an autmatic update).
**This only works from the CLI widget and the C2 for now**.

```
> update do_check_update
```

Run a task that will run sudo apt-get install ia-scribe in the background:
```
> update do_update
```

### `cameras`

The `cameras` module is responsible for interfacing with the various cameras attached
to the Scribe station. It offers a variety of informative, as well as active sub-commands.

```
> cameras                                                                
%> {u'commands': [u'add_camera_property',
               u'apply_property',
               u'are_calibrated',
               u'assign_port_to_side',
               u'get_active_cameras',
               u'get_camera_info',
               u'get_camera_port',
               u'get_camera_property',
               u'get_current_config',
               u'get_name',
               u'get_num_cameras',
               u'get_property_observers',
                ...
               u'unregister_event_types']}
```

You can call `get_active_cameras` to see the currently connected cameras.
```
> cameras get_active_cameras 
%> {'left': {'model': 'Sony Alpha-A6300 (Control)', 'port': 'usb:001,018'},
 'right': {'model': 'Sony Alpha-A6300 (Control)', 'port': 'usb:001,022'}}
```
You can even capture an image, specifying side and destination path to `take_shot`:
```
> cameras take_shot foldout /tmp/
%> 'capt0000.jpg'
```

### `stats`

This module lets you tap into the local metrics subsystem. 

```
> stats                                                                                                                                                                                                                                                                                    
%> {u'commands': [u'get_adapter',
               u'get_aggregation_metadata',
               u'get_available_aggregations_and_metadata',
               u'get_available_aggregatons',
               u'get_data',
               u'get_data_for_operator',
               u'get_icon',
               u'get_stats_by_range',
               u'log_event',
               u'partial',
               u'process_metrics_dir',
               u'process_stats']}

```

### `telemetry`

This module is a collection of some disparate utility methods that let you measure 
various aspects of the host system, like disk space, network, processor or memory utlization.

```
> telemetry                                                                                                                                                                                                                                                                             
%> {u'commands': [u'get_cpu_stats',
               u'get_dir_stats',
               u'get_fs_stats',
               u'get_nic_stats',
               u'get_temperature_stats',
               u'get_uptime_stats']}
```

```
> telemetry get_cpu_stats
%> [0.17, 0.07, 0.01]
```

```
> telemetry get_dir_stats
%> {'logs': u'9.2M', 'scribe_books': u'1.5G'}
```

### `restart`

This module only offers two options: 

```
>restart
%> {u'commands': [u'app', u'process'], u'usage': u'restart <subcommand>'}
```

`restart app` will only reload the app context, without actually terminating the process or running tasks. 
If you have installed an update, this option will not restart in the new version.
`restart process` is equivalent to closing Scribe3 and clicking on it again. This is most likely the option you want.