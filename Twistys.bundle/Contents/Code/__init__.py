import re
import random
import urllib
import urllib2 as urllib
import urlparse
import json
from datetime import datetime
from PIL import Image
from cStringIO import StringIO

GIRLSCANNERURL = 'http://www.girlscanner.com/index.php?do=search'
VERSION_NO = '1.2013.06.02.1'
DATEFORMAT = 'Released: %b-%d-%Y'
SEARCHPATH = 'http://www.twistys.com/tour/search/list/keyword/?keyword='
XPATHS = {
        'SearchResultContainer': '//div[contains(@class,"video-ui")]',
        'SearchLink': './/a[contains(@class,"info-box-video-title")]',
        'SearchTitle': './/a[contains(@class,"info-box-video-title")]',
        'SearchActor': './/div[contains(@class,"info-box-models-name")]//a',
        'MetadataDate': '/html/body/div[1]/div[1]/div/section/div/div[2]/div[1]/div[1]/div',
        'MetadataTitle': '//h1/span',
        'MetadataSummary': '//title',
        'MetadataTagline': '//h3[contains(@class,"site-name")]/a',
        'MetadataBackground': '//div[contains(@class,"player")]/img',
        'Data18PageCount': '//*[@id="centered"]/div[7]/div[2]/div[2]/form/p/b[2]'
    }

def any(s):
    for v in s:
        if v:
            return True
    return False

def PerformSearch(keyword):
    searchResults = HTML.ElementFromURL(SEARCHPATH + keyword.replace(" ","+"))
    return searchResults.xpath(XPATHS['SearchResultContainer'])

def Start():
    HTTP.CacheTime = CACHE_1DAY

def SetDateMetadata(date):
    date_object = datetime.strptime(date, DATEFORMAT)
    return date_object

def SetArtwork(metadata, details):
    backgroundUrl = details.xpath(XPATHS['MetadataBackground'])[0].get('src')
    metadata.art[backgroundUrl] = Proxy.Preview(HTTP.Request(backgroundUrl, headers={'Referer': 'http://www.google.com'}).content, sort_order = 0)

def SetPoster(metadata):
    h = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
              'Accept-Encoding': 'gzip, deflate',
              'Accept-Language': 'en-US,en;q=0.8',
              'Cache-Control': 'max-age=0',
              'Connection': 'keep-alive',
              'Content-Length': '221',
              'Content-Type': 'application/x-www-form-urlencoded',
              'Host': 'www.girlscanner.com',
              'Origin': 'http://www.girlscanner.com',
              'Referer': 'http://www.girlscanner.com/index.php?do=search',
              'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36'}

    d = {'do': 'search',
            'subaction': 'search',
            'search_start': '1',
            'result_from': '1',
            'story': metadata.title.replace("'",""),
            'titleonly': '0',
            'searchuser': '',
            'replyless': '0',
            'replylimit': '0',
            'searchdate': '0',
            'beforeafter': 'after',
            'sortby': 'title',
            'resorder': 'desc',
            'showposts': '0',
            'catlist[]': '24'}

    resultsPage = HTML.ElementFromURL(GIRLSCANNERURL,values=d,headers=h)
    results = resultsPage.xpath('//*[@id="dle-content"]//div[@class="main-news"]')
    for result in results:
        cat = result.xpath('./div[1]/div[1]/a')[0].text_content()
        if cat == 'Twistys':
            title = result.xpath('./div[1]/h2/a')[0].text_content()
            if(metadata.title.replace("'","").lower() in title.lower()):
                image = result.xpath('.//img[contains(@src,"images")]')[0].get('src')
                img_file = urllib.urlopen(image)
                im = StringIO(img_file.read())
                resized_image = Image.open(im)
                width, height = resized_image.size
                Log(str(height))
                if(height >= 600):
                    metadata.posters[image] = Proxy.Preview(HTTP.Request(image, headers={'Referer': 'http://www.google.com'}).content, sort_order = 0)        

class EXCAgent(Agent.Movies):
    name = 'Twistys'
    languages = [Locale.Language.English]
    accepts_from = ['com.plexapp.agents.localmedia']
    primary_provider = True

    def search(self, results, media, lang):
        
        title = media.name
        if media.primary_metadata is not None:
            title = media.primary_metadata.title

        for searchResult in PerformSearch(title):
            resultLink = searchResult.xpath(XPATHS['SearchLink'])[0].get('href')
            resultTitle = searchResult.xpath(XPATHS['SearchTitle'])[0].text_content().strip()
            resultActor = searchResult.xpath(XPATHS['SearchActor'])[0].text_content()
            resultID = resultLink.replace('/','_')
            score = 100 - Util.LevenshteinDistance(title.lower(), resultTitle.lower())
            results.Append(MetadataSearchResult(id = resultID, name = resultActor + " - " + resultTitle, score = score, lang = lang))
                
        results.Sort('score', descending=True)            

    def update(self, metadata, media, lang):

        Log('******UPDATE CALLED*******')
        metadata.studio = 'DDF Network'
        url = 'http://twistys.com' + str(metadata.id).replace('_','/')

        details = HTML.ElementFromURL(url)
        metadata.title = details.xpath(XPATHS['MetadataTitle'])[0].text_content()
        metadata.summary = details.xpath(XPATHS['MetadataSummary'])[0].text_content().replace('&13;', '').strip(' \t\n\r"') + "\n\n"
        metadata.tagline = details.xpath(XPATHS['MetadataTagline'])[0].text_content()
        metadata.originally_available_at = SetDateMetadata(details.xpath(XPATHS['MetadataDate'])[0].text_content())
        metadata.year = metadata.originally_available_at.year

        #Background
        SetArtwork(metadata,details)

        #Posters
        SetPoster(metadata)

        # Genres
        metadata.genres.clear()
        genres = details.xpath('//div[contains(@class,"tags-date")]//a')
        for genre in genres:
           genreName = genre.text_content().strip('\n')
           metadata.genres.add(genreName)

        metadata.roles.clear()
        metadata.collections.clear()
     
        starring = None
        starring = details.xpath('//div[contains(@class,"player-extra")]//h2//a')
        for member in starring:
            role = metadata.roles.new()
            actor = member.text_content().strip()
            role.actor = actor
            metadata.collections.add(member.text_content().strip())
