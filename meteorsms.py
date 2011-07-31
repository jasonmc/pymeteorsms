import mechanize
from BeautifulSoup import BeautifulSoup
import re
import urllib
from urlparse import urljoin


import sys, logging
logger = logging.getLogger("mechanize")
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)
#logger.setLevel(logging.DEBUG)



br = mechanize.Browser()

br.addheaders = [("User-Agent", "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2.7) Gecko/20100713 Firefox/3.6.7")]


br.open("http://meteor.ie")


for f in br.forms():
    if f.attrs['id'] == "MyMeteorLogin":
        loginForm = f

assert(loginForm)

br.form = loginForm

br.set_handle_robots(False)


br["msisdn"] = "REDACTED"
br["pin"] = "REDACTED"

r2 = br.submit()


l = br.find_link(url_regex="freeweb")

br.follow_link(l)




d = br.response().get_data()
soup = BeautifulSoup(d)
print "Texts remaining:", soup.find(id = "numfreesmstext")['value']


regex = re.compile("var CFID = (\d*);")
r = regex.search(d)
cfid = r.groups()[0]
regex = re.compile("var CFTOKEN = (\d*);")
r = regex.search(d)
cftoken = r.groups()[0]



#we can't click anything anymore, let's do the ajax requests ourselves



number = "0|REDACTED" #TODO: might need to prepend "0|"

number = urllib.quote(number.encode("utf-8"))


#geturl "/mymeteorapi/index.cfm?event=smsAjax&CFID=99999&CFTOKEN=99999&func=addEnteredMsisdns"
#urlencoded form query:  "ajaxRequest=addEnteredMSISDNs&remove=-&add="+encodeURI(number)

url = "/mymeteorapi/index.cfm?event=smsAjax&CFID=%s&CFTOKEN=%s&func=addEnteredMsisdns" % (cfid,cftoken)
url = urljoin(br.geturl(),url)
data = "ajaxRequest=addEnteredMSISDNs&remove=-&add="+number

r1 = br.open(url,data)







text = "can't believe it works!!"

text = urllib.quote(text.encode("utf-8"))

#geturl "/mymeteorapi/index.cfm?event=smsAjax&func=sendSMS&CFID=REDACTED&CFTOKEN=REDACTED"
#urlencoded form query: "ajaxRequest=sendSMS&messageText=" + encodeURI(text)

url = "/mymeteorapi/index.cfm?event=smsAjax&func=sendSMS&CFID=%s&CFTOKEN=%s" %(cfid,cftoken)
url = urljoin(br.geturl(),url)
data = "ajaxRequest=sendSMS&messageText=" + text

r2 = br.open(url,data)






############################### FOR REFERENCE ###############################


#smsRecall becomes  "/mymeteorapi/index.cfm?event=smsAjax&CFID=REDACTED&CFTOKEN=REDACTED"

#need to add recipients using AJAX!!
"""
var CFID = REDACTED;
var CFTOKEN = REDACTED;
var smsRecall = "/mymeteorapi/index.cfm?event=smsAjax";


    msisdnDetailObj.value="0|"+getEl("quickSearchMsisdn").value;

    searchValue=getEl("msisdnDetail").value;
    AddEnteredMSISDN=new AjaxRequest(smsRecall + "&func=addEnteredMsisdns","ajaxRequest=addEnteredMSISDNs&remove=-&add="+encodeURIComponent(searchValue),"addEnteredMSISDN",7000); 

"""



"""
smsText=getEl("smsComposeTextArea").value;

    ajaxURL="/mymeteorapi/index.cfm?event=smsAjax&func=sendSMS&CFID=REDACTED&CFTOKEN=REDACTED";
    ajaxParams="ajaxRequest=sendSMS&messageText="+encodeURIComponent(smsText);
//  window.open(ajaxURL);

    switchPane("fwtSent");
    hideEl("groupError");
    hideEl("singleError");
    hideEl("systemError");
    showEl("sendingText");
    hideEl("sentTrue");
    hideEl("sentFalse");
    sendLeText=new AjaxRequest(ajaxURL,ajaxParams,"sendSMS",7000);
}
"""
