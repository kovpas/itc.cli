Disclaimer
=======

**This script is still on early beta stage, so use it at your own risk.**

itc.cli
=======

iTunesConnect command line interface **β**

Script allows to add/edit metadata and uploads of the application through iTunesConnect without user interaction.

This is my first ever application written in python, so, please don't judge too strict ;)

Installation
=======

Dependencies: [lxml](http://lxml.de/installation.html), [html5lib](http://code.google.com/p/html5lib/wiki/UserDocumentation), [requests](http://docs.python-requests.org/en/latest/user/install/)

Usage
=======

```` ./itc.py --username apple_id --password my_password````

````--password```` parameter is not mandatory, so you can input password manually after script startup

If all dependencies installed properly, you will see something like this:

````itc.cli.git kovpas$ ./itc.py --username apple_id````  
> "Password:  
INFO:root:Login: logged in. Session cookies are saved to .itc-cli-cookies.txt  
INFO:root:Application found: "App 1" (123456789)  
INFO:root:Application found: "App 2" (987654321)  
INFO:root:Nothing to do."

Every time you run the script, it uses cookies which are stored in the file ````.itc-cli-cookies.txt```` and checks if cookies are still valid or script needs to log in again. That means that once you've entered your password, you don't need it as long as session lives on iTunesConnect's servers. 

Party begins with ````--config_file```` parameter:

````./itc.py --username apple_id --config_file actions.json````

Config file format
=======

Config file is a simple JSON file (please note, that it's a _strict_ JSON. You must avoid construcations like **,]** or **,}** (i.e. ````[1,2,]```` or ````{"a":"avalue", "b": "bvalue",}````). If your config file contains errors, you'll get an exception with the exact position of a wrong character)

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
Uploads images. If ````indexes```` are provided 