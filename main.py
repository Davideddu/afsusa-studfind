#!/usr/bin/env python2
# -*- coding: utf-8 -*-

__version__ = 0.2

import os, sys, contextlib, json, random, subprocess, thread, time, urllib

def hide_keyboard(*args, **kwargs):
    pass

persistence = False
try:
    import shelve
    persistence = True
except ImportError:
    persistence = False

# "opsys" is set to "android" if running on an Android Linux device,
# to "linux" if running on a generic GNU/Linux or BSD distro, to "macosx"
# if running on a Mac and to "win" if running on Windows.
opsys = "linux"
try: 
    import android
    print "Running an Android device"
    android.init()
    #browser = android.AndroidBrowser()
    opsys = "android"
    def hide_keyboard(*args, **kwargs):
        android.hide_keyboard()
except ImportError:
    if sys.platform.startswith('darwin'):
        opsys = "macosx"
    elif os.name == 'nt':
        opsys = "win"
    elif os.name == "posix":
        opsys = "linux"

curdir = os.path.dirname(os.path.realpath(__file__))

# Took from Python 2.7 "user" module; Android support added
home = curdir                          # Default
if opsys == "android":
    home = "/mnt/sdcard"
elif 'HOME' in os.environ:
    home = os.environ['HOME']
elif os.name == 'posix':
    home = os.path.expanduser("~/")
elif os.name == 'nt':                   # Contributed by Jeff Bauer
    if 'HOMEPATH' in os.environ:
        if 'HOMEDRIVE' in os.environ:
            home = os.environ['HOMEDRIVE'] + os.environ['HOMEPATH']
        else:
            home = os.environ['HOMEPATH']


import kivy

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import DictProperty, StringProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
if persistence:
    from kivy.uix.filechooser import FileChooserIconView


class Container(object):
    shown = False
    def dismiss(self, *args, **kwargs):
        pass

def open_url(url):
    if opsys == "macosx":
        subprocess.Popen(['open', url])
    elif opsys == 'win':
        os.startfile(url)
    elif opsys == "linux":
        subprocess.Popen(['xdg-open', url])
    elif opsys == "android":
        android.open_url(url)

global container, taptime
container = Container()
taptime = time.time()

# This widget is customized in the .kv file; that's why it's empty!
class NiceBoxLayout(BoxLayout):
    pass

class ZipFindApp(App):
    def build(self):
        self.root = NiceBoxLayout(orientation="vertical")
        self.api = "http://www.afsusa.org/site/searchStudents/?zipcode={0}"

        self.title = "AFS USA Student Finder"

        from data import zips

        self.shelf = {"data":  [],
                      "bios":      [],
                      "zips_done": [],
                      "zips_todo": zips.zips[:],
                      "justrun:":  True}

        self.students = []

        random.shuffle(self.shelf["zips_todo"])
        del zips

        self.toolbar = BoxLayout(orientation="horizontal", padding=5, spacing=5, height=45, size_hint=(1, None))
        self.filterbar = BoxLayout(orientation="horizontal", padding=5, spacing=5, height=45, size_hint=(1, None))

        self.resultslist = GridLayout(cols=1, padding=5, spacing=5, size_hint=(1, None))
        self.resultslist.bind(minimum_height=self.resultslist.setter('height'))

        scroll = ScrollView(pos_hint={'center_x': .5, 'center_y': .5}, do_scroll_x=False, size_hint=(1, 1))
        scroll.add_widget(self.resultslist)

        self.root.add_widget(self.toolbar)
        self.root.add_widget(scroll)
        self.root.add_widget(self.filterbar)

        # Working ZIP code for testing purposes: 98058
        self.zipentry = TextInput(text='ZIP Code', font_size=20, height=45, multiline=False, on_text_validate=self.ui_search)
        self.nameentry = TextInput(text='Name', font_size=20, height=45, multiline=False, on_text_validate=self.ui_autosearch)
        self.nameentry.bind(text=self.filter)
        self.helpbutton = Button(on_press=hide_keyboard, on_release=self.show_help, height=40, width=40, size_hint=(None, None), background_normal=os.path.join(curdir, "images/help_normal.png"), background_down=os.path.join(curdir, "images/help_down.png"))
        self.autosearchbutton = Button(on_press=hide_keyboard, on_release=self.ui_autosearch, height=40, width=40, size_hint=(None, None), background_normal=os.path.join(curdir, "images/autosearch_normal.png"), background_down=os.path.join(curdir, "images/autosearch_down.png"))
        self.searchbutton = Button(on_press=hide_keyboard, on_release=self.ui_search, height=40, width=40, size_hint=(None, None), background_normal=os.path.join(curdir, "images/search_normal.png"), background_down=os.path.join(curdir, "images/search_down.png"), background_disabled_normal=os.path.join(curdir, "images/search_disabled.png"), background_disabled_down=os.path.join(curdir, "images/search_disabled.png"))
        self.toolbar.add_widget(self.zipentry)
        self.toolbar.add_widget(self.nameentry)
        self.toolbar.add_widget(self.helpbutton)

        if persistence:
            self.persbutton = Button(on_press=hide_keyboard, on_release=self.ui_load_persistence, height=40, width=40, size_hint=(None, None), background_normal=os.path.join(curdir, "images/persistence_normal.png"), background_down=os.path.join(curdir, "images/persistence_down.png"))

        self.toolbar.add_widget(self.persbutton)
        self.toolbar.add_widget(self.autosearchbutton)
        self.toolbar.add_widget(self.searchbutton)

        self.sports = Spinner(
            text='Any sport',
            values=["Any sport", 'Badminton', 'Baseball', 'Basketball', 'Bicycling', 'Boating', 'Cheerleading', 'Dance', 'Diving', 'Field Hockey', 'Football', 'Golf', 'Gymnastics', 'Handball', 'Horseback Riding', 'Ice Hockey', 'Martial Arts', 'Running', 'Skating', 'Skiing', 'Soccer', 'Softball', 'Swimming', 'Tennis', 'Track', 'Volleyball'],
            size_hint=(None, None),
            height=40)
        self.sports.bind(text=self.filter)
        self.music = Spinner(
            text='Any music',\
            values=["Any music", "Guitar", "Piano", "Singing"],
            size_hint=(None, None),
            height=40)
        self.music.bind(text=self.filter)
        self.genders = Spinner(
            text='Any gender',
            values=("Any gender", "Male", "Female"),
            size_hint=(None, None),
            height=40)
        self.genders.bind(text=self.filter)
        self.interests = Spinner(
            text='Any interest',
            values=["Any interest", 'Computer', 'Cooking', 'Environment', 'Fishing', 'Games/cards', 'Gardening', 'Movies', 'Museums', 'Photography', 'Reading', 'Shopping', 'Television', 'Theater', 'Travel', 'Video Games', 'Volunteering'],
            size_hint=(None, None),
            height=40)
        self.interests.bind(text=self.filter)
        self.countries = Spinner(
            text="Any country",
            values=("Any country", 'Albania', 'Argentina', 'Armenia', 'Australia', 'Austria', 'Azerbaijan', 'Bahrain', 'Bangladesh', 'Belgium', 'Bolivia', 'Bosnia and Herzegovina', 'Brazil', 'Bulgaria', 'Cameroon', 'Canada', 'Chile', 'China', 'Colombia', 'Costa Rica', 'Croatia', 'Czech Republic', 'Denmark', 'Dominican Republic', 'Ecuador', 'Egypt', 'Finland', 'France', 'Gaza', 'Georgia', 'Germany', 'Ghana', 'Greenland', 'Guatemala', 'Honduras', 'Hong Kong', 'Hungary', 'Iceland', 'India', 'Indonesia', 'Israel', 'Italy', 'Japan', 'Kazakhstan', 'Kenya', 'Kosovo', 'Kuwait', 'Kyrgyzstan', 'Latvia', 'Lebanon', 'Liberia', 'Libya', 'Macedonia', 'Malaysia', 'Mali', 'Mexico', 'Moldova', 'Morocco', 'Mozambique', 'Netherlands', 'New Zealand', 'Nigeria', 'Norway', 'Oman', 'Pakistan', 'Panama', 'Paraguay', 'Peru', 'Philippines', 'Portugal', 'Qatar', 'Russia', 'Saudi Arabia', 'Senegal', 'Sierra Leone', 'Slovakia', 'Slovenia', 'South Africa', 'South Korea', 'Spain', 'Sweden', 'Switzerland', 'Tajikistan', 'Tanzania', 'Thailand', 'Tunisia', 'Turkey', 'Turkmenistan', 'Ukraine', 'West Bank', 'Yemen', "Any country"),
            size_hint=(None, None),
            height=40)
        self.countries.bind(text=self.filter)
        self.group_names = {
            "Interests":    self.interests,
            "Music":        self.music,
            "Sports":       self.sports
        }
        self.filterbar.add_widget(Widget(size_hint=(1, None)))
        self.filterbar.add_widget(self.sports)
        self.filterbar.add_widget(self.music)
        self.filterbar.add_widget(self.genders)
        self.filterbar.add_widget(self.interests)
        self.filterbar.add_widget(self.countries)

        self.bind(on_start=self.post_build_init, on_stop=self.pre_close)

        self.resultslist.add_widget(Label(text="\n\nSearch something to start.", halign="center"))

        return self.root

    def ui_search(self, *args):
        self.resultslist.clear_widgets()
        self.resultslist.add_widget(Label(text="\n\nLoading...", halign="center"))
        thr = thread.start_new_thread(self.search_thread, ())

    def search_thread(self):
        self.shelf["justrun"] = False
        studs = self.load_zip(self.zipentry.text)
        self.resultslist.clear_widgets()
        self.shelf["bios"] = []
        self.students = []

        if not studs:
            self.resultslist.add_widget(Label(text="\n\nNo results found.", halign="center"))
        elif type(studs) == type(str()):
           self.resultslist.add_widget(Label(text="\n\n" + studs, halign="center")) 
        else:
            for stud in studs:
                self.shelf["data"].append(stud)
                #print self.shelf["data"]
                self.process_stud(stud, self.zipentry.text)
        return None

    def process_stud(self, stud, zipcode):
        stud["zipcode"] = zipcode
        for i in stud["interests"]:
            try:
                if not i["name"] in self.group_names[i["group_names"]].values:
                    self.group_names[i["group_names"]].values.append(i["name"])
            except KeyError:
                pass
        if not stud["bio"] in self.shelf["bios"]:
            student = Student(data=stud)
            if self.to_add(student):
                self.resultslist.add_widget(student)
            self.shelf["bios"].append(stud["bio"])
            self.students.append(student)

    def load_zip(self, zipcode):
        try:
            with contextlib.closing(urllib.urlopen(self.api.format(zipcode))) as f:
                js = json.loads(f.read())
            if not js["success"]:
                return None
            else:
                return js["students"]
        except IOError:
            return "Couldn't connect to AFS. Please check your connection."


    def ui_autosearch(self, *args):
        if self.shelf["zips_done"] == 0:
            self.resultslist.clear_widgets()
        self.searchbutton.background_disabled_normal=os.path.join(curdir, "images/search_disabled.png")
        self.searchbutton.background_disabled_down=os.path.join(curdir, "images/search_disabled.png")
        self.searchbutton.unbind(on_release=self.ui_search)
        self.autosearchbutton.background_disabled_normal=os.path.join(curdir, "images/autosearch_disabled.png")
        self.autosearchbutton.background_disabled_down=os.path.join(curdir, "images/autosearch_disabled.png")
        self.autosearchbutton.unbind(on_release=self.ui_autosearch)
        self.autosearchthread = thread.start_new_thread(self.autosearch_thread, ())

    def on_search_finished(self):
        self.searchbutton.background_normal=os.path.join(curdir, "images/search_normal.png")
        self.searchbutton.background_down=os.path.join(curdir, "images/search_down.png")
        self.searchbutton.bind(on_release=self.ui_search)
        self.autosearchbutton.background_normal=os.path.join(curdir, "images/autosearch_normal.png")
        self.autosearchbutton.background_down=os.path.join(curdir, "images/autosearch_down.png")
        self.autosearchbutton.bind(on_release=self.ui_autosearch)
        self.root.remove_widget(self.statlabel)
        self.root.remove_widget(self.progressbox)

    def autosearch_thread(self):
        self.shelf["justrun"] = False
        self.statlabel = Label(halign="center", size_hint_y=None, height="16dp")
        self.progressbox = BoxLayout(orientation="horizontal", height="7dp", size_hint_y=None, padding=[6, 0, 6, 2])
        self.statprogress = ProgressBar(max=len(self.shelf["zips_done"])+len(self.shelf["zips_todo"]), size_hint_y=None, height="5dp")
        self.progressbox.add_widget(self.statprogress)
        self.root.add_widget(self.statlabel, 2)
        self.root.add_widget(self.progressbox, 3)

        count = 0

        while len(self.shelf["zips_todo"]) > 0:
            zipcode = self.shelf["zips_todo"][0][:]
            self.shelf["zips_todo"].remove(zipcode)
            self.shelf["zips_done"].append(zipcode)
            count += 1
            time1 = time.time()
            if count <= 3:
                self.statlabel.text = "Checking {0}... ({1}/{2})".format(zipcode, len(self.shelf["zips_done"]), len(self.shelf["zips_todo"]))
            else:

                humantime = self.humanize_time(deltaT * len(self.shelf["zips_todo"]))
                self.statlabel.text = "Checking {0}... ({1}/{2}, {4} ZIPs/sec, ETA {3})".format(zipcode, len(self.shelf["zips_done"]), len(self.shelf["zips_todo"]), humantime, round(deltaT, 2))
            self.statprogress.value = len(self.shelf["zips_done"])
            studs = self.load_zip(zipcode)
            if not studs:
                time2 = time.time()
                continue
            elif type(studs) == type(str()):
                self.resultslist.add_widget(Label(text="\n\n" + studs, halign="center"), len(self.resultslist.children))
                break
            else:
                for stud in studs:
                    self.shelf["data"].append(stud)
                    self.process_stud(stud, zipcode)
            time2 = time.time()
            deltaT = time2-time1
        self.on_search_finished()
        return None

    def humanize_time(self, time):
        sec = int(round(time))
        mins = 0
        hours = 0
        strtime = ""
        if sec / 60. > 1:
            mins = (sec - (sec % 60)) / 60
            sec = sec % 60
        if mins / 60. > 1:
            hours = (mins - (mins % 60)) / 60
            mins = mins % 60
        if hours > 0:
            strtime += "{0} h ".format(hours)
        if mins > 0 or hours != 0:
            strtime += "{0} m ".format(mins)
        if (sec > 0 and hours == 0) or mins != 0:
            strtime += "{0} s".format(sec)
        else:
            strtime = strtime[:-1]
        return strtime

    def filter(self, *args):
        try:
            if not self.shelf["justrun"]:
                #print "filtering"
                studs = self.students[:]
                self.resultslist.clear_widgets()
                for stud in studs:
                    if self.to_add(stud):
                        self.resultslist.add_widget(stud)
        except KeyError:
            pass

    def to_add(self, stud):
        to_add = False
        for i in stud.data["interests"]:
            try:
                if (i["name"] == self.group_names[i["group_name"]].text or "Any" in self.group_names[i["group_name"]].text) and i["group_name"] == "Music":
                    to_add = True
            except KeyError:
                pass
        if not to_add: return False

        to_add = False
        for i in stud.data["interests"]:
            try:
                if (i["name"] == self.group_names[i["group_name"]].text or "Any" in self.group_names[i["group_name"]].text) and i["group_name"] == "Interests":
                    to_add = True
            except KeyError:
                pass
        if not to_add: return False

        to_add = False
        for i in stud.data["interests"]:
            try:
                if (i["name"] == self.group_names[i["group_name"]].text or "Any" in self.group_names[i["group_name"]].text) and i["group_name"] == "Sports":
                    to_add = True
            except KeyError:
                pass
        if not to_add: return False

        if stud.data["sex"] != self.genders.text and not "Any" in self.genders.text:
            return False
        if stud.data["country_name"] != self.countries.text and not "Any" in self.countries.text:
            return False
        if not self.nameentry.text.lower() in stud.data["name"].lower() and not self.nameentry.text == "Name":
            return False
        return True

    def ui_load_persistence(self, *args):
        content = BoxLayout(orientation="vertical", padding=5, spacing=5)
        popup = Popup(size_hint=(.9, .9), content=content, title="Select persistence file")
        self.chooser = DavChooser()
        self.chooser.fileentry.bind(on_text_validate=self.on_load_persistence)

        checkboxbox = BoxLayout(orientation="horizontal", spacing=5, size_hint_x=None)#, height="25dp")
        self.resetcheckbox = CheckBox(size_hint_x=None)
        label = Label(text="Reset file content", size_hint_x=None)
        checkboxbox.add_widget(self.resetcheckbox)
        checkboxbox.add_widget(label)


        buttonbox = BoxLayout(orientation="horizontal", size_hint_y=None, spacing=5, height="50dp")
        load = Button(on_press=hide_keyboard, text="Load", on_release=self.on_load_persistence, height="40dp", size_hint=(None, None))
        cancel = Button(on_press=hide_keyboard, text="Cancel", on_release=popup.dismiss, height="40dp", size_hint=(None, None))
        buttonbox.add_widget(checkboxbox)
        buttonbox.add_widget(Widget(size_hint_y=None))
        buttonbox.add_widget(cancel)
        buttonbox.add_widget(load)

        content.add_widget(self.chooser)
        content.add_widget(buttonbox)

        global container
        container.popup = popup
        def onopen(*args, **kwargs):
            global container
            container.shown = True
        def ondismiss(*args, **kwargs):
            global container
            container.shown = False
        self.bind(on_open=onopen, on_dismiss=ondismiss)
        popup.open()

    def on_load_persistence(self, *args):
        container.popup.dismiss()
        self.load_persistence(os.path.join(self.chooser.path, self.chooser.filename), self.resetcheckbox.active)

    def load_persistence(self, shelf, reset):
        #print "load_persistence"
        realshelf = shelve.open(shelf, writeback=True)

        if reset or not "data" in realshelf.keys():
            realshelf["data"] = self.shelf["data"][:]

        if reset or not "zips_done" in realshelf.keys():
            realshelf["zips_done"] = self.shelf["zips_done"][:]

        if reset or not "zips_todo" in realshelf.keys():
            realshelf["zips_todo"] = self.shelf["zips_todo"][:]

        realshelf["bios"] = self.shelf["bios"][:]

        self.shelf = realshelf
        self.shelf["justrun"] = len(self.shelf["zips_done"]) == 0 and len(self.shelf["data"]) == 0
        print len(self.shelf["zips_done"]) == 0 and len(self.shelf["data"]) == 0

        if not self.shelf["justrun"]:
            self.resultslist.clear_widgets()
        for i in self.shelf["data"]:
            self.process_stud(i, i["zipcode"])


    def show_help(self, *args):
        popup = Popup(size_hint=(.8, .8), auto_dismiss=True, title="Help")
        popup.content = BoxLayout(orientation="vertical", spacing=5, padding=5)
        scroll = ScrollView(pos_hint={'center_x': .5, 'center_y': .5}, do_scroll_x=False, size_hint=(1, 1))
        popup.content.add_widget(scroll)
        scrollbox = GridLayout(cols=1, padding=5, spacing=5, size_hint=(1, None))
        scrollbox.bind(minimum_height=scrollbox.setter('height'))
        scroll.add_widget(scrollbox)
        close = Button(on_press=hide_keyboard, text="Close", on_release=popup.dismiss, height="40dp", size_hint=(1, None))
        popup.content.add_widget(close)

        def on_ref(instance, value):
            if value == "email":
                open_url("mailto:david.dep.1996@gmail.com")
            elif value == "site":
                open_url("http://davideddu.altervista.org/software/")
            elif value == "gpl":
                open_url("http://gnu.org/licenses/gpl.html")
            elif value == "donate":
                open_url("http://davideddu.altervista.org/blog/donate/")

        label = Label(markup=True, size_hint_y=None, halign="center", on_ref_press=on_ref)

        label.height = int((215. * len(label.text)) / 600)# * (596. / self.label.width))
        def setsize(instance, value):
            #print len(instance.text), instance.text.split("\n", 1)[0], instance.width
            instance.text_size[0] = value[0]
            instance.texture_size[1] = value[1]
            instance.height = int((215. * len(label.text)) / 600 * (596. / instance.width))
        label.bind(size=setsize)  #self.label.setter("texture_size"))

        oses = {"linux":    "Linux",
                "android":  "Android",
                "macosx":   "Mac OS X",
                "win":      "Windows (use this program on Linux for best performance)"}

        label.text = """[size=24dp][b]AFS USA Student Finder[/b] {version}[/size]
by [ref=email][color=#32A4CE]Davide Depau[/color][/ref] - [ref=site][color=#32A4CE]Homepage[/color][/ref]
Running on {0}

AFS USA Student Finder is Free Software, but its development takes precious time.
You can [ref=donate][color=#32A4CE]donate[/color][/ref] to help its development.

[size=20dp][b]How to use the application[/b][/size]
Use this application as you would with any touch app: to scroll, don't use the mouse wheel, just drag the items, like you would do with your phone.

[size=16dp][b]Normal search[/b][/size]
It is like in the AFS website: just write a zip code in the first box, and tap the "search" button (the one with the lens).
Wait a few seconds, and it will show a list of students going near to the ZIP you put. You can filter them using the menus on the bottom, or using the "Name" box. Tapping the "Show more" button will show a lot of information, most of which is not available in AFS website.

[size=16dp][b]Automatic search[/b][/size]
When you click the "Autosearch" button, the program will check one by one all the ZIP codes. This might be useful if you are going to go the USA with AFS and you want to find your profile.
Please note that:
- this operation requires a lot of time (if you are lucky, about ten hours...)
- once started the operation cannot be stopped/paused unless you close the application
- slow PCs or phones may become very slow while running this software
- your carrier may charge you if you use it with mobile broadband
- the application cannot manage very big amounts of data, so you should enable some filters (like the country, the gender and the name) before starting the operation

If you are running this application on a mobile phone/tablet, please also note that if you do something else while the app is working, the Android OS might close the app to free some resources needed by the other applications.

[size=16dp][b]Persistence[/b][/size]
«Automatic search is very slow and takes a lot of hours! Can I close the application and make it start where it had finished?»
Of course you can! When you open the app, [b]before searching anything[/b], click on the "persistence" button (the floppy). Choose a file; you can create a new one or choose an existing one. Then click "Load". If you previously used the same file, the program will automatically load the old student list. You can then start autosearch: it will continue from the point it has been stopped.
If you want to create a new list on the same file, enable "Reset file content" before clicking "Load".

Pros:
- You don't have to keep the PC turned on to parse the entire list of ZIPs
- You don't lose your list if the app crashes for any reason

Cons:
- It doesn't work on Android
- The persistence may become very big

[size=12dp]I am not in any way related to AFS, AFS USA or other associations/companies. Every trademark is of his respective owner. I decline every responsibility due to the use of this program to the user.
Copyright © Davide Depau 2013.  This program is licensed under a GNU GPL version 3 license or later [ref=gpl]<[color=#32A4CE]http://gnu.org/licenses/gpl.html[/color]>\[/ref].
This is free software: you are free to change and redistribute it. There is NO WARRANTY, to the extent permitted by law.[/size]""".format(oses[opsys], version=__version__)

        scrollbox.add_widget(label)

        global container
        container.popup = popup
        def onopen(*args, **kwargs):
            global container
            container.shown = True
        def ondismiss(*args, **kwargs):
            global container
            container.shown = False
        self.bind(on_open=onopen, on_dismiss=ondismiss)
        popup.open()

    def on_pause(self, *args):
        return True

    def on_resule(self, *args):
        pass

    def post_build_init(self, ev):
        # Map Android keys
        if opsys == 'android':
            android.map_key(android.KEYCODE_MENU, 1000)
            android.map_key(android.KEYCODE_BACK, 1001)
            android.map_key(android.KEYCODE_SEARCH, 1002)
            win = self._app_window
            def _key_handler(a, key, b, c, d):
                global container
                if key == 1001:
                    android.hide_keyboard() 
                    if container.shown:
                        try:
                            container.popup.dismiss()
                        except:
                            sys.exit(0)
                    else:
                        global taptime
                        t = time.time()
                        if t - taptime <= 1:
                            # Double tap
                            sys.exit(0)
                        else:
                            label = Label(text="Press Back again to exit", halign="center", size_hint=(1, None), height=20)
                            self.root.add_widget(label, 1)
                            container.label = label
                            def rmlabel(*args, **kwargs):
                                global container
                                self.root.remove_widget(container.label)
                                del container.label
                            Clock.schedule_once(rmlabel, 1)
                        taptime = t
                elif key == 1000:
                    if not container.shown:
                        self.show_help()
                    else: container.popup.dismiss()
            win.bind(on_keyboard=_key_handler)

    def pre_close(self, *args):
        try:
            self.shelf.close()
        except AttributeError:
            pass


class Student(BoxLayout):
    data = DictProperty() 

    def __init__(self, **kwargs):
        super(Student, self).__init__(**kwargs)
        self.image_api = "http://www.afsusa.org/images/meet_students/flags/{0}-flag.gif"
        self.orientation = "horizontal"
        self.size_hint_y = None
        #self.height = "150dp"
        self.spacing = "5dp"
        self.padding = "5dp"

        self.flag = AsyncImage(source=self.image_api.format(self.data["country_name"].lower().replace(" ", "-")), size_hint_x=None, width="80dp")

        middlebox = BoxLayout(orientation="vertical")
        self.namelabel = Label(text="Meet {0} from {1}".format(self.data["name"], self.data["country_name"]), font_size="24dp", bold=True, italic=self.data["hidden"])
        self.namelabel.bind(size=self.namelabel.setter("text_size"))
        middlebox.add_widget(self.namelabel)

        biolabel = Label(text=self.data["short_bio"])


        biolabel.bind(size=self._setsize)    #biolabel.setter("text_size"))


        middlebox.add_widget(biolabel)

        morebutton = Button(text="Show\nmore", size_hint_x=None, on_press=hide_keyboard, on_release=self.show_popup)

        self.add_widget(self.flag)
        self.add_widget(middlebox)
        self.add_widget(morebutton)

    def show_popup(self, *args):
        popup = StudentPopup(data=self.data, title="Meet {0} from {1}".format(self.data["name"], self.data["country_name"]), flag=self.flag.source)
        popup.open()

    def _setsize(self, instance, value):
        h = instance.texture_size[1] + self.namelabel.texture_size[1] + 10
        if h < self.flag.height:
            h = self.flag.height
        self.height = h
        instance.text_size[0] = value[0]
        instance.texture_size[1] = value[1]

class StudentPopup(Popup):
    data = DictProperty()
    flag = StringProperty()

    def __init__(self, **kwargs):
        super(StudentPopup, self).__init__(**kwargs)
        self.size_hint = (0.8, 0.8)
        self.auto_dismiss = True

        self.content = BoxLayout(orientation="vertical", spacing=5, padding=5)
        scroll = ScrollView(pos_hint={'center_x': .5, 'center_y': .5}, do_scroll_x=False, size_hint=(1, 1))
        self.content.add_widget(scroll)
        self.scrollbox = GridLayout(cols=1, padding=5, spacing=5, size_hint=(1, None))
        self.scrollbox.bind(minimum_height=self.scrollbox.setter('height'))
        scroll.add_widget(self.scrollbox)
        close = Button(on_press=hide_keyboard, text="Close", on_release=self.dismiss, height="40dp", size_hint=(1, None))
        self.content.add_widget(close)

        self.label = Label(markup=True, size_hint_y=None)

        attributes = ""
        if self.data["hidden"]:
            attributes = "\n[b]Attributes:[/b] [i]Hidden[/i]"
        if self.data["priority"]:
            if attributes == "":
                attributes = "\n[b]Attributes:[/b] [i]Priority[/i]"
            else:
                attributes = "\n[b]Attributes:[/b] [i]Hidden, Priority[/i]"

        self.label.text = u"""[b]Name:[/b] {0}
[b]Gender:[/b] {1}
[b]Country:[/b] {2}
[b]Zip code:[/b] {9}
[b]Region:[/b] {3}
[b]Area:[/b] {4}
[b]Interests:[/b] {5}
[b]Progress:[/b] {6}{7}

{8}""".format(self.data["name"], self.data["sex"], self.data["country_name"], self.data["region"], self.data["area"], self.data["interest_string"], self.data["progress"], attributes, self.data["bio"], self.data["zipcode"])

        # 250:600=x:len
        self.label.height = int((250. * len(self.label.text)) / 600)
        def setsize(instance, value):
            instance.text_size[0] = value[0]
            instance.texture_size[1] = value[1]
            instance.height = int((250. * len(instance.text)) / 600 * (596. / instance.width))

        self.label.bind(size=setsize)  #self.label.setter("texture_size"))


        self.scrollbox.add_widget(Widget())
        self.scrollbox.add_widget(AsyncImage(source=self.flag, size_hint_y=None, width="120dp"))
        self.scrollbox.add_widget(self.label)

        global container
        container.popup = self
        def onopen(*args, **kwargs):
            global container
            container.shown = True
        def ondismiss(*args, **kwargs):
            global container
            container.shown = False
        self.bind(on_open=onopen, on_dismiss=ondismiss)

class DavChooser(BoxLayout):
    filename = StringProperty("")
    chooser = ObjectProperty(None, allownone=True)
    path = StringProperty(home)

    def __init__(self, **kwargs):
        super(DavChooser, self).__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = "5dp"
        self.chooser = FileChooserIconView(path=self.path)
        self.chooser.bind(selection=self.on_file_select, path=self.setter("path"))
        self.fileentry = TextInput(size_hint_y=None, height="30dp", text=self.filename, multiline=False)
        self.fileentry.bind(text=self.setter("filename"))
        self.davbar = BoxLayout(orientation="horizontal", size_hint_y=None, height="45dp", spacing="5dp")
        self.levelup = Button(on_press=hide_keyboard, on_release=self.on_levelup, height=40, width=40, size_hint=(None, None), background_normal=os.path.join(curdir, "images/levelup_normal.png"), background_down=os.path.join(curdir, "images/levelup_down.png"))
        self.newdir = Button(on_press=hide_keyboard, on_release=self.on_newdir, height=40, width=40, size_hint=(None, None), background_normal=os.path.join(curdir, "images/newdir_normal.png"), background_down=os.path.join(curdir, "images/newdir_down.png"))
        self.davbar.add_widget(self.levelup)

        scroll = ScrollView(pos_hint={'center_x': .5, 'center_y': .5}, do_scroll_y=False, size_hint=(1, 1))
        self.navbar = GridLayout(cols=1, orientation="horizontal", spacing=5, padding=[5, 0, 0, 0])
        self.navbar.bind(minimum_height=self.navbar.setter('height'))
        scroll.add_widget(self.navbar)

        self.davbar.add_widget(scroll)
        self.davbar.add_widget(self.newdir)

        self.chooser.bind(path=self.on_path)
        self.on_path(None, self.path)

        self.add_widget(self.davbar)
        self.add_widget(self.fileentry)
        self.add_widget(self.chooser)

    def on_path(self, instance, path):

        splitpath = os.path.abspath(path).split(os.sep)
        self.navbar.clear_widgets()
        if splitpath[0] == "":
            splitpath[0] = os.sep
        #print splitpath

        for i in splitpath:
            if i != "":
                btn = Button(text=i, on_press=hide_keyboard, on_release=self.navigate, height=40, size_hint=(None, None))
                btn.path = os.path.normpath(os.sep.join(splitpath[:splitpath.index(i)+1]))
                #print "buttonpath", btn.path, splitpath[:splitpath.index(i)+1], "i:", i, splitpath.index(i)
                self.navbar.cols = len(self.navbar.children) + 1
                self.navbar.add_widget(btn)

    def on_levelup(self, *args):
        #print "levelup", os.sep.join(self.chooser.path.split(os.sep)[:-1]), self.chooser.path
        newpath = os.sep.join(self.chooser.path.split(os.sep)[:-1])
        if newpath == "":
            newpath = os.sep
        self.chooser.path = newpath

    def on_newdir(self, *args):
        content = BoxLayout(orientation="vertical", spacing="5dp")
        self.popup = Popup(size_hint=(.5, .5), content=content, title="New folder")
        buttonbox = BoxLayout(orientation="horizontal", spacing="5dp", height=45)
        ok = Button(text="OK", on_press=hide_keyboard, on_release=self.mkdir, height=40, size_hint_y=None)
        cancel = Button(text="Cancel", on_press=hide_keyboard, on_release=self.popup.dismiss, height=40, size_hint_y=None)
        buttonbox.add_widget(ok)
        buttonbox.add_widget(cancel)
        self.direntry = TextInput(height=30, size_hint_y=None, on_text_validate=self.mkdir, multiline=False)
        content.add_widget(self.direntry)
        content.add_widget(buttonbox)
        self.popup.open()

    def mkdir(self, *args):
        #print "mkdir", os.path.join(self.chooser.path, self.direntry.text)
        os.mkdir(os.path.join(self.chooser.path, self.direntry.text))
        # This should make the view refresh
        self.chooser.path = os.sep + self.chooser.path[:]
        self.popup.dismiss()

    def navigate(self, button):
        #print "navigate", button.path
        self.chooser.path = button.path

    def on_file_select(self, instance, selection):
        try:
            self.fileentry.text = selection and os.path.basename(selection[0]) or ""
        except:
            self.fileentry.text = ""
        self.filename = selection[0]


if __name__ == '__main__':
    app = ZipFindApp()
    app.run()