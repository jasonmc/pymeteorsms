import mechanize
from BeautifulSoup import BeautifulSoup
import re
import urllib


# import sys, logging
# logger = logging.getLogger("mechanize")
# logger.addHandler(logging.StreamHandler(sys.stdout))
# logger.setLevel(logging.INFO)
#logger.setLevel(logging.DEBUG)


USERNAME = "REDACTED"
PASSWORD = "REDACTED"


def getphonebook():
    """Parse the meteorsms phoenbook"""
    pass



def send_text(number,text):

    assert(number.isdigit())

    br = mechanize.Browser()

    #TODO: save and loading of cookies!

    br.addheaders = [("User-Agent", "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2.7) Gecko/20100713 Firefox/3.6.7")]
    br.set_handle_robots(False) # sorry, but otherwise it looks for a non-existent robots.txt and seems to block


    br.open("http://meteor.ie")


    for f in br.forms():
        if f.attrs['id'] == "MyMeteorLogin":
            loginForm = f
    assert(loginForm)
    br.form = loginForm


    br["msisdn"] = USERNAME
    br["pin"] = PASSWORD

    login_response = br.submit()


    br.follow_link(br.find_link(url_regex="freeweb"))


    data = br.response().get_data()
    soup = BeautifulSoup(data)
    print "Texts remaining:", soup.find(id = "numfreesmstext")['value']


    regex = re.compile("var CFID = (\d*);")
    try:
        r = regex.search(data)
        cfid = r.groups()[0]
    except:
        raise Exception("Could not get CFID!")
    regex = re.compile("var CFTOKEN = (\d*);")
    try:
        r = regex.search(data)
        cftoken = r.groups()[0]
    except:
        raise Exception("Could not get CFTOKEN!")



    #we can't click anything anymore, let's do the ajax requests ourselves

    url = "/mymeteorapi/index.cfm?event=smsAjax&CFID=%s&CFTOKEN=%s&func=addEnteredMsisdns" % (cfid,cftoken)
    data = "ajaxRequest=addEnteredMSISDNs&remove=-&add=" + urllib.quote(("0|" + number).encode("utf-8"))
    r1 = br.open(url,data)


    url = "/mymeteorapi/index.cfm?event=smsAjax&func=sendSMS&CFID=%s&CFTOKEN=%s" %(cfid,cftoken)
    data = "ajaxRequest=sendSMS&messageText=" + urllib.quote(text.encode("utf-8"))
    r2 = br.open(url,data)

    #TODO: ensure these responses are 200 OK and not 301 moved temporarily

    #TODO: make these neater by using encodeuri to build the data part



def main():
    
    send_text("REDACTED","cool")


if __name__ == "__main__":
    main()




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
