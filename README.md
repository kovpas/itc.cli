Disclaimer
=======

**This script is still in beta state, so use it at your own risk.**

itc.cli
=======
iTunesConnect command line interface.

Script allows to add/edit metadata, uploads and in-app purchases of the application through iTunesConnect without user interaction.

Have you ever had to create 1000 inapp purchases by template? Or may be to upload 15 localized screenshots for each of 25 languages you app supports? This script does that for you :)  
<sub>This is my first ever application written in python, so, please don't judge me too harshly ;)</sub>

&bull; [Installation](#installation)  
&bull; [iTC login](#itc-login)  
&bull; [Update application metadata](#update-application-metadata)  
&bull; [Create new application](#create-new-application)  
&bull; [Create new application version](#create-new-application-version)  
&bull; [Promo codes](#promo-codes)  
&bull; [Reviews](#reviews)  
&bull; [Logging](#logging)  
&bull; [Roadmap](#roadmap)  
&bull; [License](#license)  
Installation
=======

### Automatic

* Install [pip](http://www.pip-installer.org/en/latest/installing.html)
* ````[sudo] pip install [--upgrade] itc.cli```` (use upgrade in case if you already have itc linstalled)

### Semi-automatic

* Install [setuptools](https://pypi.python.org/pypi/setuptools)
* Download sources somewhere on your computer
* ````sudo python setup.py install````

### Manual

* Download sources somewhere on your computer
* Install dependencies: [lxml](http://lxml.de/installation.html), [html5lib](http://code.google.com/p/html5lib/wiki/UserDocumentation), [requests](http://docs.python-requests.org/en/latest/user/install/) (v0.14.2), [docopt](https://github.com/docopt/docopt) (v0.6.1), [beautifulsoup](http://www.crummy.com/software/BeautifulSoup/) (v4.2.1), [keyring](https://pypi.python.org/pypi/keyring#source-installation) (v3.3)
* ````export PYTHONPATH=${PYTHONPATH}:/path/to/itc.cli/source/directory````
* ````export PATH=${PATH}:/path/to/itc.cli/source/directory/itc/bin````

Now ````itc```` command is available to run

iTC login
=======

```` itc login --username apple_id --password my_password````

````--password```` parameter is not mandatory, so you can input password manually and securely after script startup

If all dependencies installed properly, you will see something like this:

```` itc login --username apple_id````  
> Password:  
INFO:root:Login: logged in. Session cookies are saved to .itc-cli-cookies.txt  
INFO:root:Application found: "App 1" (123456789)  
INFO:root:Application found: "App 2" (987654321)  
INFO:root:Nothing to do.

Every time you run the script, it uses cookies which are stored in the file ````.itc-cli-cookies.txt```` and checks if cookies are still valid or script needs to log in again. That means that once you've entered your password, you don't need to enter it anymore as long as session is alive on iTunesConnect's servers. In case if you want to ignore cookie file and re-enter credentials, add ````--no-cookies```` parameter.

You can also store password in a system's secure storage (i.e. keychain on OS X), using ````--store-password```` key:  
```` itc login --store-password --username apple_id````  
Thus password will be taken from a secure storage every time session on iTunesConnect is expired.  

You also can delete stored password, using ````--delete-password```` parameter:  
```` itc login --delete-password --username apple_id````  

Update application metadata
=======

Party starts with ````--config_file```` parameter:

````itc update --username apple_id --config-file actions.json````

Config file is a simple JSON file (please note, that it's a _strict_ JSON. You must avoid constructions like **,]** or **,}** (i.e. ````[1,2,]```` or ````{"a":"avalue", "b": "bvalue",}````). If your config file contains errors, you'll get an exception with the exact position of a wrong character).

Metadata
-------

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

You can also use files as a source of data for "whats new", "description" and "keywords":
```` JSON
{
  "general" : {
      "name"               : "My application - default",
      "whats new"          : {"file name format": "app data/whats new - {language}.txt"},
  }
}
````

So, itc.cli during iteration through languages will replace {language} with appropriate language id (i.e. "pt", "en" and so on).

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

#### Delete  
If ````indexes```` are provided, deletes images by selected indexes. Otherwise deletes all images

#### Upload  
Uploads images. If ````indexes```` are provided, only images with selected indexes will be uploaded

#### Sort  
Sorts images. ````indexes```` are mandatory for this command

#### Replace  
Replaces existing images with new ones. If ````indexes```` are not provided, deletes all images and uploads new ones

#### How to select images to upload  
There's an option in ````config```` section:
```` JSON
{
    "images": {
        "file name format": "images/{language}/{device_type} {index}.png"
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
------

At the moment, 4 of 5 inapp types are supported: 'Consumable', 'Non-Consumable', 'Free Subscription', 'Non-Renewing Subscription'

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
  "review screenshot": "images/inapp.png",
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
    "indexes": [19, 20, 22]
  },
  "id": "ru.kovpas.itc.cli.test.1.inapp.{index}",
  "type": "Non-Renewing Subscription",
  "reference name": "Test inapp - {index}",
  "price tier": {
    "19-20": 1,
    "22": 2
  },
  "cleared": false,
  "hosting content with apple": false,
  "review notes": "Notes",
  "review screenshot": "images/inapp.png",
  "general": {
    "name": ["My first inapp", "My second inapp", "My third inapp"],
    "description": {
      "19": "My first inapp description",
      "20": "My second inapp description",
      "22": "My third inapp description"
    },
    "publication name": "Publication inapp - {index}"
  },
  "languages": {
    "en": {
      "name": ["My first inapp - en", "My second inapp - en", "My third inapp - en"],
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

Script iterates through ````indexes```` array and creates inapp purchase. For the example above 3 inapps will be created.

Every ````{index}```` keyword in strings is replaced by corresponding index.  
Arrays and dictionaries are also supported, so you could provide an array or dictionary instead of string. See example above for format reference. 

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

Application review notes
-------

This part of configuration is self-explanatory 

````JSON
{
  "app review information": {
      "first name": "f name",
      "last name": "l name",
      "email address": "not_an_email@address.com",
      "phone number": "+3101234567",
      "review notes": {"file name format": "app data/Review notes.txt"}
      "username" : "uname",
      "password" : "pword",
  }
}
````

Create new application
=======

In order to create a new application, you should use ````create```` command and provide a configuration file:  
````./itc/bin/itc create -c newapp.json````

Configuration file looks similar to the one, which you use for ````update````. It contains same ````config```` and ````application```` sections. In ````application```` section two subsections are mandatory: ````app review information```` (see [Application review notes](#application-review-notes) for more info) and ````new app````.

````JSON
{
  "new app": {
            "default language"       : "en",
            "name"                   : "testapp9.itc.com",
            "sku number"             : "testapp9.itc.com",
            "bundle id"              : "*",
            "bundle id suffix"       : "testapp9.itc.com",
            "availability date"      : "Jan 01 2014",
            "countries"              : {"type": "include", "list":["Iceland", "Fiji"]},
            "price tier"             : 0,
            "discount"               : false,
            "version"                : "1.0",
            "copyright"              : "Company",
            "primary category"       : "Games",
            "primary subcategory 1"  : "Adventure",
            "primary subcategory 2"  : "Racing",
            "secondary category"     : "Health & Fitness",
            "app rating"             : [0, 1, 0, 1, 2, 0, 1, 2, 0, 0],
            "large app icon"         : {"file name format": "app data/icon.png"},
            "screenshots"            : {"iphone": [1], "iphone 5": [1]},
            "eula text"              : "EULA Text. This param supports 'file name format' property",
            "eula countries"         : {"type": "exclude", "list":["Iceland", "Fiji"]},
            "description"            : "Short description",
            "keywords"               : "keywords",
            "support url"            : "http://support_url_default.com",
            "marketing url"          : "http://marketing_url_default.com",
            "privacy policy url"     : "http://support_url_default.com"
        }
}
````

A couple of notes. The following fields are optional:  
* ````countries```` - if not provided, all countries are included  
* ````discount```` - false by default  
* ````eula text````  
* ````eula countries```` - if not provided, all countries are included  
* ````marketing url````  
* ````privacy policy url````  

The following fields support both string and [````file name format````](#metadata) option:  
* ````eula text````  
* ````description````  
* ````keywords````  

Create new application version
=======

In order to create a new application version, you should use ````version```` command and provide a configuration file:  
````./itc/bin/itc version -c version.json````

This file should contain ````application```` dictionary with the following fields: ````id```` (optional, could be passed with ````-a```` command line key), ````version```` and ````metadata````:

````JSON
{
    "application": {
        "id": 585307074,
        "version": "2.0",
        "metadata": {
            "general" :{
                "whats new": {"file name format": "whats new - {language}.txt"}
            },
            "languages": {
                "en": {
                    "whats new": "test cli - en"
                },
                "pt": {
                    "whats new": "test cli - pt"
                },
                "en-GB": {
                    "whats new": "test cli - en-gb"
                }
            }
        }
    }
}
````


Automagically generate config file
=======

With ````generate```` command script creates json file ({application_id}.json), which contains metadata for each language of the application. In case if no ````--application-id```` parameter passed to script, it iterates through all the applications for current account. If you want to include inapps into a generated configuration file, add ````--generate-config-inapp```` parameter.

Promo codes
=======

With ````promo```` command, script generates a certain amount of promocodes for a specified application and either prints them to console or writes to a file:  
````./itc/bin/itc promo 3 -a APP_ID -o promocodes.txt````

Please note, that 'Ready for Sale' version must exist for application.

Reviews
=======

Use ````reviews```` command, to download reviews in JSON format:  
````./itc/bin/itc reviews -a APP_ID -o reviews.txt````

By default, itc will fetch all available reviews, but you can use ````-l```` option to limit scope to latest version only.  
You may also specify a date range to get reviews. In order to do that, use ````-d```` property:

````./itc/bin/itc reviews ... -d 13/06/2013-18/06/2013```` - this will fetch all reviews within specified period  
````./itc/bin/itc reviews ... -d 13/06/2013-```` - this will fetch all reviews starting from 13th of June  
````./itc/bin/itc reviews ... -d -13/06/2013```` - this will fetch all reviews up to 13th of June  
````./itc/bin/itc reviews ... -d 13/06/2013```` - this will fetch all reviews matching exact date - 13th of June  

Date format could be ````dd/mm/yyyy````, ````today````, ````yesterday```` or a number of days from today:

````./itc/bin/itc reviews ... -d yesterday```` - reviews for yesterday (not including today! to include today, use ````yesterday-````)  
````./itc/bin/itc reviews ... -d 6-```` - reviews for last 6 days  


Logging
=======  

You may want to see additional logs. It is possible with ```` -v ```` and ```` -vv ```` options:  
```` ./itc/bin/itc -vv ...````  
```` -v ```` shows what itc is acually doing  
```` -vv ```` prints results of HTTP requests to a console.
```` -f ```` nicely formats html response. May be used only with -vv option.

There's also an option of silent mode, so only errors are printed to a console:
```` ./itc/bin/itc -s ...````

Roadmap
=======  

There are several features planned to be implemented:  
* ~~inapp purchases management~~  
* ~~promo codes~~  
* ~~user reviews~~  
* sales reports  

License
=======
itc.cli is available under the MIT license.

