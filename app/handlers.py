import os
import webapp2
import jinja2
import logging
import json
import urllib2
import fnmatch
import re
import calendar
import glob
import datetime
import PyRSS2Gen
import operator

from app.engine import * 
from google.appengine.api import search

NUMBER_OF_POSTS_ON_MAIN_PAGE = 7
NUMBER_OF_POSTS_ON_RSS_FEED = 50

class DefaultHandler(webapp2.RequestHandler):
    def get(self, year = '', month = ''):

        items = []
        files = ArticleManager.get_files()

        if year == '':
            files = files[:NUMBER_OF_POSTS_ON_MAIN_PAGE]

        items = [ArticleManager.get_article(filename) for filename in files if (year == '') or (year == filename[:4] and month == filename[4:6])]

        key = 'home' if year == '' else 'montly-archive-' + year + '-' + month
        self.response.write(ArticleManager.get_view(key, {'items': items, 'page': 'HOME' if year == '' else 'MONTHLY_ARCHIVE' }))

    def head(self, year = '', month = ''):
        pass        

    def handle_404(self, request, response, exception):
        logging.exception(exception)
        response.set_status(404)
        response.write(ArticleManager.get_view('404', {'page': '404'}))

    def handle_500(self, request, response, exception):
        logging.exception(exception)
        response.set_status(500)
        response.write(ArticleManager.get_view('500', {'page': '500'}))    

class ArchiveHandler(webapp2.RequestHandler):
    def get(self):
        files = ArticleManager.get_files()

        archive = []
        section = None

        for filename in files:
            year = filename[:4]
            month = filename[4:6]

            if section is None or section.year != year:
                section = Section(year, ArticleManager.get_article(filename))
                archive.append(section)
            else:
                section.add(ArticleManager.get_article(filename))

        self.response.write(ArticleManager.get_view('archive', {'archive': archive, 'page': 'ARCHIVE' }))            

    def head(self):
        pass

class AboutHandler(webapp2.RequestHandler):
    def get(self):
        posts = len(ArticleManager.get_files())
        self.response.write(ArticleManager.get_view('about', {'posts': posts, 'page': 'ABOUT' }))            

    def head(self):
        pass

class PostHandler(webapp2.RequestHandler):
    def get(self, year, month, day, page):
        article = self.get_article(year, month, day, page)

        if article is not None:
            key = year + month + day + '-' + page

            related_articles = Mapping.get_related_articles(article)

            self.response.write(ArticleManager.get_view(key, {'items': [article], 'related_articles': related_articles, 'page': 'POST' }))
        else:
            DefaultHandler(response = self.response).handle_404(None, self.response, ErrorArticleNotFound(year, month, day, page))

    def head(self, year, month, day, page):
        article = self.get_article(year, month, day, page)
        if article is None:
            DefaultHandler(response = self.response).handle_404(None, self.response, ErrorArticleNotFound(year, month, day, page))

    def get_article(self, year, month, day, page):
        try:
            filename = year + month + day + '-' + page + '.html'
            return ArticleManager.get_article(filename)
            
        except jinja2.TemplateNotFound as e:
            return None

class RSSHandler(webapp2.RequestHandler):
    def get(self):
        rss = MemcacheManager.get('rss')
        if rss is None:
            items = []
            files = ArticleManager.get_files()[:NUMBER_OF_POSTS_ON_RSS_FEED]
            for filename in files:
                article = ArticleManager.get_article(filename)

                item = PyRSS2Gen.RSSItem(
                    title = article['title'],
                    link = article['url'],                    
                    description = article['html'],
                    content = article['html'],
                    guid = PyRSS2Gen.Guid(article['url']),
                    pubDate = article['dateTime'])

                items.append(item)

            rss = PyRSS2Gen.RSS2(
                title = "Opposite Reasons",
                link = webapp2.uri_for('home', _full=True),
                feedLink = webapp2.uri_for('rss', _full=True),
                description = "Opposite Reasons RSS feed",
                lastBuildDate = datetime.datetime.now(),
                items = items).to_xml()

            MemcacheManager.add('rss', rss)

        self.response.content_type = 'application/rss+xml'    
        self.response.charset = 'iso-8859-1'    
        self.response.write(rss)   

    def head(self):
        self.response.content_type = 'application/rss+xml'    
        self.response.charset = 'iso-8859-1'    

class Section():
    def __init__(self, year, article):
        self.year = year
        self.articles = []
        self.add(article)

    def add(self, article):
        self.articles.append(article)        
