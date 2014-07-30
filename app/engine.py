import os
import webapp2
import jinja2
import datetime
import calendar
import re
import glob
import operator
import json
import urllib
from google.appengine.api import memcache

MEMCACHE_ENABLED = os.environ['SERVER_SOFTWARE'].startswith('Google App Engine')

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.PackageLoader('app', 'templates'),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
JINJA_ENVIRONMENT.globals['year'] = datetime.date.today().year

class ArticleManager:
    @staticmethod
    def get_article(filename):
        year = filename[:4]
        month = filename[4:6]
        day = filename[6:8]
        key = 'article-' + filename[:-5]

        article = MemcacheManager.get(key)
        if article is not None:
            return article
        else:
            html = JINJA_ENVIRONMENT.get_template('articles/' + year + '/' + month + '/' + filename).render()
            title = re.findall('<h1>(.+?)</h1>', html)[0]
            html = re.sub('<h1>(.+?)</h1>', '', html, count=1)
            name = filename[9:-5]

            metadata = re.findall('@metadata: ({.+?})', html, re.DOTALL)
            metadata = json.loads(metadata[0]) if len(metadata) == 1 else None

            if metadata is not None:
                html = re.sub('@metadata: ({.+?})', '', html, count=1, flags=re.DOTALL) 

                if "tags" in metadata:
                    metadata["tags"] = [tag.strip() for tag in metadata["tags"].split(',')]
                else:
                    metadata["tags"] = []

                if "summary" not in metadata:
                    metadata["summary"] = title

                if "lang" not in metadata:
                    metadata["lang"] = "en"
            else:
                metadata = { "summary": title, "tags": [], "lang": "en" }

            article = { 
                'id': key,
                'filename': filename,
                'url2': urllib.quote_plus(webapp2.uri_for('post', _full=True, year=year, month=month, day=day, page=name)),
                'html': html, 
                'formattedLongDate': calendar.month_name[int(month)] + ' ' + str(int(day)) + ', ' + year,
                'formattedShortDate': month + '/' + day + '/' + year,
                'dateTime': datetime.datetime(int(year), int(month), int(day)),
                'title': title,
                'link': '/' + year + '/' + month + '/' + day + '/' + name, 
                'url': webapp2.uri_for('post', _full=True, year=year, month=month, day=day, page=name),
                'summary': metadata["summary"],
                'lang': metadata["lang"],
                'tags': metadata["tags"] 
            }

            MemcacheManager.add(key, article)

            return article

    @staticmethod
    def get_view(key, data, shell = 'shell.html'):
        page = MemcacheManager.get(key)
        if page is not None:
           return page
        else:
           page = JINJA_ENVIRONMENT.get_template(shell).render(data)
           MemcacheManager.add(key, page)
           return page

    @staticmethod
    def get_files(filename = '2*.html'):
        files = MemcacheManager.get("files-" + filename)
        if files is None:
            files = sorted(glob.glob('app/templates/articles/*/*/' + filename), reverse=True) 
            index = 0
            for filename in files:
                files[index] = filename[len('app/templates/articles/0000/00/'):]
                index += 1

            MemcacheManager.add("files-" + filename, files)
        
        return files

class Mapping():
    @staticmethod
    def get_mappings():
        mappings = MemcacheManager.get("mappings")
        if mappings is None:
            mappings = {}

            files = ArticleManager.get_files()
            for filename in files:
                article = ArticleManager.get_article(filename)

                if article["tags"] is not None:
                    for tag in article["tags"]:
                        if tag not in mappings:
                            mappings[tag] = []

                        mappings[tag].append(article["filename"])

            MemcacheManager.add("mappings", mappings)

        return mappings

    @staticmethod
    def get_related_articles(article):
        mappings = Mapping.get_mappings()

        mapping_hits = {}
        for tag in article["tags"]:
            for article_filename in mappings.get(tag, ""):
                if article_filename != "" and article_filename != article["filename"] and ArticleManager.get_article(article_filename)["lang"] == article["lang"]:
                    if article_filename not in mapping_hits:
                        mapping_hits[article_filename] = 0

                    mapping_hits[article_filename] += 1

        related_articles = sorted(sorted(mapping_hits.iteritems(), key=operator.itemgetter(0), reverse=True), key=operator.itemgetter(1), reverse=True)[:3]
        related_articles = [ArticleManager.get_article(a[0]) for a in related_articles]

        if len(related_articles) < 3:
            files = ArticleManager.get_files()

            index = 0
            while len(related_articles) < 3 and index < len(files):
                article_filename = files[index]

                if article_filename != article["filename"] and article_filename not in mapping_hits and article["lang"] == ArticleManager.get_article(article_filename)["lang"]:
                    related_articles.append(ArticleManager.get_article(article_filename))
                index += 1

        return related_articles

class MemcacheManager:
    @staticmethod
    def get(key):
        if MEMCACHE_ENABLED is True:
            return memcache.get(key)

        return None

    @staticmethod
    def add(key, value):
        memcache.add(key=key, value=value)

class ErrorArticleNotFound(Exception):
    def __init__(self, year, month, day = None, page = None):
        self.year = year
        self.month = month
        self.day = day
        self.page = page

    def __str__(self):
        if self.day is None:
            self.day = 'none'

        if self.page is None:
            self.page = 'none'

        return 'Error loading article with the following information: [Year: ' + self.year + '. Month: ' + self.month + '. Day: ' + self.day + '. Page: ' + self.page + ']'

def encode(value):
    return urllib.quote_plus(value)

JINJA_ENVIRONMENT.filters['encode'] = encode
