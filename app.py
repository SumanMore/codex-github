import os
import json
from gevent import monkey
monkey.patch_all()

from userdata import logger
from fuzzywuzzy import fuzz
from dotenv import load_dotenv
from pymongo import MongoClient
from gevent.pywsgi import WSGIServer
from flask import Flask, url_for, render_template, request

load_dotenv()

dburl = os.environ.get('MONGODB_URI')

client = MongoClient(dburl)
db = client.get_default_database()
members = db.members

app = Flask(__name__, static_url_path='/static')

@logger.catch
def getContent():
    data = []

    for mem in members.find():
        data.append(mem)

    data = sorted(data, key=lambda k: k['totalCommits'])

    return data[::-1]

@logger.catch
@app.route("/")
def index():
    global content
    global total
    content = getContent()
    total = sum([x['totalCommits'] for x in content])
    return render_template('index.html', context=content, totalC=total, search=False)

@logger.catch
@app.route("/search")
def searchMember():
    query = request.args.get("query")

    if query == "":
        return render_template('search.html', context=content, search=True, found=True)

    # logger.debug(query)
    sanitize = lambda x: x.lower() if x else " "
    ratios = [ { "ratio" : max([fuzz.partial_ratio(sanitize(x['name']), query.lower()), fuzz.partial_ratio(sanitize(x['username']), query.lower())]), "data": x } for x in content ]
    
    ratios = sorted(ratios, key=lambda k: k['ratio'])
    
    result = [ x['data'] for x in ratios if x['ratio'] > 60 ][::-1]

    found = len(result) != 0
    
    return render_template('search.html', context=result, search=True, found=found)

@logger.catch
@app.route("/<username>")
def profile(username):
    try:
        user_details = [x for x in members.find({"username" : username})].pop()
        # logger.debug(user_details)

        return render_template("profile.html", user=user_details)
    except IndexError:
        logger.error(f'Username not found. username:{username}')
        return "404"
    except Exception as e:
        logger.error(e)
        raise e

    

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    http_server = WSGIServer(('', port), app.wsgi_app)
    logger.debug("Server ready: ")
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        logger.debug("Exiting")

