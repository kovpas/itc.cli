Disclaimer
=======

**This script is still on early beta stage, so use it at your own risk.**

itc.cli
=======
iTunesConnect command line interface **β**

Script allows to add/edit metadata, uploads and in-app purchases of the application through iTunesConnect without user interaction.

This is my first ever application written in python, so, please don't judge me too harshly ;)

License
=======
itc.cli is available under the MIT license.

Installation
=======

Dependencies: [lxml](http://lxml.de/installation.html), [html5lib](http://code.google.com/p/html5lib/wiki/UserDocumentation), [requests](http://docs.python-requests.org/en/latest/user/install/)

Usage
=======

```` ./itc/bin/itc --username apple_id --password my_password````

````--password```` parameter is not mandatory, so you can input password manually after script startup

If all dependencies installed properly, you will see something like this:

```` ./itc/bin/itc --username apple_id````  
> Password:  
INFO:root:Login: logged in. Session cookies are saved to .itc-cli-cookies.txt  
INFO:root:Application found: "App 1" (123456789)  
INFO:root:Application found: "App 2" (987654321)  
INFO:root:Nothing to do.

Every time you run the script, it uses cookies which are stored in the file ````.itc-cli-cookies.txt```` and checks if cookies are still valid or script needs to log in again. That means that once you've entered your password, you don't need to enter it anymore as long as session is alive on iTunesConnect's servers. 

Party begins with ````--config_file```` parameter:

````./itc/bin/itc --username apple_id --config-file actions.json````

Config file format
=======

Config file is a simple JSON file (please note, that it's a _strict_ JSON. You must avoid constructions like **,]** or **,}** (i.e. ````[1,2,]```` or ````{"a":"avalue", "b": "bvalue",}````). If your config file contains errors, you'll get an exception with the exact position of a wrong character)

Commands object has two fields - 'general' and 'languages'. Script merges each language's object with 'general' object. For example:

```` JSON
{
  "general" : {
      "name"               : "My application - default",
      "whats new"          : "What's new - default"
  },
  "languages" : {
      "en" : {
          "whats new": "What's new - en"
      },
      "pt" : {
          "name"     : "My application - pt"
      }
  }
}
````

In the example above the following values will be assigned:

For English language:  
````
"name"               : "My application - default",  
"whats new"          : "What's new - en"
````  
For Brasilian Portugese:  
````
"name"               : "My application - pt",  
"whats new"          : "What's new - default" 
````  

Now the most interesting part - images. Images object contains three fields:
* iphone
* iphone 5
* ipad

Each field's value is an array of commands (well, in 99% of cases you'll need only one command).

There are four commands for updating images:  
* Delete ('d')
* Upload ('u')
* Sort ('s')
* Replace ('r')

### Delete  
If ````indexes```` are provided, deletes images by selected indexes. Otherwise deletes all images

### Upload  
Uploads images. If ````indexes```` are provided, only images with selected indexes will be uploaded

### Sort  
Sorts images. ````indexes```` are mandatory for this command

### Replace  
Replaces existing images with new ones. If ````indexes```` are not provided, deletes all images and uploads new ones

### How to select images to upload  
There's an option in ````config```` section:
```` JSON
{
    "images": {
        "filename_format": "images/{language}/{device_type} {index}.png"
    }
}
````

Imagine you have the following folder structure:
````
itc.cli.git\
    images\
        en\
            iphone 2.png
            iphone 5 2.png
            ipad 4.png
        pt\
            iphone 1.png
            iphone 2.png
            iphone 3.png
            iphone 4.png
            iphone 5.png <- 5th screenshot for 3.5" iPhone
            iphone 5 1.png <- 1st screenshot for 4" iPhone
            iphone 5 2.png
            ipad 1.png
            ipad 2.png
            ipad 3.png
            ipad 4.png
````

So, if you write the following command:

````"ipad": [{"cmd": "u"}]````  
One iPad screenshot will be uploaded for English language and four for Portugese. Please, note that you have to make sure that there are enough space for these screenshots.

````"iphone": [{"cmd": "r"}]````  
This command replaces second screenshot for English language and replaces all screenshots for Portugese.

Of course for each language you can specify exact indexes of replaced/deleted and uploaded screenshots:
```` JSON
{
  "general" : {
      "images": {
          "iphone"  : [{"cmd": "d", "indexes": [3]}],
          "iphone 5": [{"cmd": "r"}],
          "ipad"    : [{"cmd": "u"}]
      }
  },
  "languages" : {
      "en" : {
          "images": {
              "iphone"  : "", <- don't modify iPhone screenshots for English language
              "iphone 5": [{"cmd": "u", "indexes": [2]}] <- instead of replacing all screenshots for iPhone 5, upload one with name 'iphone 5 2.png'
          }
      },
      "pt" : {
          "images": {
              "iphone": [{"cmd": "s", "indexes": [1, 3, 5, 4, 2]}] <- apply new sorting
          }
      }
  }
}
````

In the example above, all iPad and pt/iPhone 5 screenshots will be uploaded by generic rule. The rest are specific for each language.


In-App purchases
=======

At the moment, only 4 of 5 inapp types are supported: 'Consumable', 'Non-Consumable', 'Free Subscription', 'Non-Renewing Subscription'

There are two ways of managing inapps. The first one is one by one:

````JSON
[{       
  "id": "ru.kovpas.itc.cli.test.1.inapp.1",
  "type": "Non-Consumable",
  "reference name": "Test inapp",
  "price tier": 2,
  "cleared": false,
  "hosting content with apple": false,
  "review notes": "Notes",
  "general": {
    "name": "Test inapp",
    "description": "Description inapp",
    "publication name": "Publication inapp" <- only used for appropriate inapps 
  },
  "languages": {
    "en": {
      "name": "Test inapp - en",
      "description": "Description inapp - en",
    },
    "ru": {
      "publication name": "Publication inapp - ru"
    },
    "pt": {
      "description": "Description inapp - pt",
    }
  }
}, {2nd inapp}, {3rd inapp}, ...]
````

The second one is by using templates. 

````JSON
{
  "index iterator": {
    "indexes": [1, 3, 5]
  }
  "id": "ru.kovpas.itc.cli.test.1.inapp.{index}",
  "type": "Non-Renewing Subscription",
  "reference name": "Test inapp - {index}",
  "price tier": 2,
  "cleared": false,
  "hosting content with apple": false,
  "review notes": "Notes",
  "general": {
    "name": "Test inapp - {index}",
    "description": "Description inapp - {index}",
    "publication name": "Publication inapp - {index}"
  },
  "languages": {
    "en": {
      "name": "Test inapp - {index} - en",
      "description": "Description inapp - {index} - en",
    },
    "ru": {
      "publication name": "Publication inapp - {index} - ru"
    },
    "pt": {
      "description": "Description inapp - {index} - pt",
    }
  }
}
````

Script iterates through ````indexes```` array and creates inapp purchase. Every ````{index}```` keyword is replaced by corresponding index. For the example above 3 inapps will be created.

Another way is to create start and end indexes:
````JSON
{
  "index iterator": {
    "from": 7,
    "to": 9
  }
}
````

If ````from```` index is not provided, 1 is used. ````to```` index is mandatory.

Roadmap
=======

Two features are planned to be implemented: inapp purchases management and promo codes.  
... and may be sales reports.
