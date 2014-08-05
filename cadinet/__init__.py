# Copyright 2014 Johannes Reinhardt <jreinhardt@ist-dein-freund.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from flask import Flask, render_template, request, flash, redirect, url_for, g, abort, jsonify, send_file
from flask.ext.pymongo import PyMongo
from flask.ext.openid import OpenID
from flask_wtf import Form
from wtforms import TextField
from wtforms.validators import DataRequired, URL
from werkzeug import secure_filename

from urlparse import urljoin

from os import environ, mkdir, makedirs
from os.path import exists,join
from shutil import rmtree
import os.path
import sys
import logging
from logging.handlers import RotatingFileHandler
import random
import re

app = Flask(__name__)
app.config.from_pyfile(join(environ['OPENSHIFT_REPO_DIR'],'mongo.cfg'))
app.config.from_pyfile(join(environ['OPENSHIFT_DATA_DIR'],'cadinet.cfg'))

mongo = PyMongo(app)

oid_path = join(environ['OPENSHIFT_DATA_DIR'],'openid')
if not exists(oid_path):
    mkdir(oid_path)
oid = OpenID(app, oid_path,safe_roots=[])

#log_handler = RotatingFileHandler(join(environ['OPENSHIFT_LOG_DIR'],'cadinet.log'),maxBytes=2**20,backupCount=3)
#log_handler.setLevel(logging.INFO)
#log_handler.setFormatter(logging.Formatter(
#    '%(asctime)s %(levelname)s: %(message)s '
#    '[in %(pathname)s:%(lineno)d]'
#))
#
#app.logger.addHandler(log_handler)
#logging.getLogger().addHandler(log_handler)

class OpenIDForm(Form):
    url = TextField("url",validators=[DataRequired(),URL(require_tld=True)])

class SubmissionForm(Form):
    url = TextField("url",validators=[DataRequired(),URL(require_tld=True)])

class SearchForm(Form):
    query = TextField("query",validators=[DataRequired()])


@app.route('/')
def home():
    return redirect(url_for("about"))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register',methods=['GET','POST'])
@oid.loginhandler
def register():
    form = OpenIDForm()
    if form.validate_on_submit():
        openid = form.url.data
        return oid.try_login(openid, ask_for=['email', 'nickname'])
    return render_template('register.html', form = form,next=oid.get_next_url(),
                           error=oid.fetch_error())

@oid.after_login
def provide_token(resp):
    user = {
        '_id' : resp.identity_url,
        'email' : resp.email,
        'name' : resp.nickname,
        'token' : "%x" % random.SystemRandom().getrandbits(64)
    }
    if (not user['email'] is None) and (not user['name'] is None):
        users = mongo.db.users
        #check if user is already registered
        if users.find_one({"_id" : user['_id']}) is None:
            users.insert(user)
            return render_template('token.html',token = user['token'],action="created")
        else:
            users.update({"_id" : user['_id']},user)
            return render_template('token.html',token = user['token'],action="updated")
    else:
        redirect(url_for('register'))

@app.route('/clear')
def clear():
    mongo.db.things.remove()
    return "cleared"

@app.route('/thing/<id>')
def show_thing(id):
    things = mongo.db.things
    return render_template('thing.html',thing = things.find_one({"_id" : id}))

@app.route('/things')
def list_things():
    things = mongo.db.things
    for thing in things.find():
        print thing

    return render_template('things.html',things = things.find())

def allowed_file(exts,filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in exts

@app.route('/upload/fcstd/<id>',methods=['POST'])
def upload_fcstd(id):
    thing = mongo.db.things.find_one({"_id" : id})
    if thing is None:
        abort(404)
    #TODO: authenticate upload
    res = {}
    file = request.files['file']
    if file and allowed_file('fcstd',file.filename):
        filename = secure_filename(file.filename)
        thing_dir = join(environ['OPENSHIFT_DATA_DIR'],'things',id,'fcstd')
        if not exists(thing_dir):
            makedirs(thing_dir)
        file.save(os.path.join(thing_dir, filename))
        thing['fcstd_file'] = filename
        mongo.db.things.update({'_id' : id},thing)
        res["status"] = 'success'
    else:
        res["status"] = 'failed'
    return jsonify(**res)

@app.route('/download/fcstd/<id>')
def download_fcstd(id):
    thing = mongo.db.things.find_one({"_id" : id})
    if thing is None or not 'fcstd_file' in thing:
        abort(404)
    return send_file(join(environ['OPENSHIFT_DATA_DIR'],'things',id,'fcstd',thing['fcstd_file']),mimetype='application/x-extension-fcstd',as_attachment=True,attachment_filename=os.path.basename(thing['fcstd_file']))

@app.route('/upload/3djs/<id>',methods=['POST'])
def upload_3djs(id):
    thing = mongo.db.things.find_one({"_id" : id})
    if thing is None:
        return jsonify(status="fail",message="No thing with ID %s found" % id),404
    req = request.get_json()
    if not req:
        return jsonify(status="fail",message="There was a problem with the request"),400

    users = mongo.db.users
    if "token" in req:
        user = users.find_one({"token" : req["token"]})
        if user is None:
            return jsonify(status="fail",message="Authentication failed"),403
    else:
        return jsonify(status="fail",message="No authentication token given"),403

    if not ("vertices" in req and "facets" in req and "camera" in req):
        return jsonify(status="fail",message="No 3D data supplied"),400

    #check data TODO jsonschema
    #TODO camera
    if not isinstance(req["vertices"],list):
        return jsonify(status="fail",message="Invalid vertices list"),400
    for v in req["vertices"]:
        if not isinstance(v,list):
            return jsonify(status="fail",message="Invalid vertex coordinates"),400
        if not len(v) == 3:
            return jsonify(status="fail",message="Invalid vertex coordinates"),400
        for c in range(3):
            if not isinstance(v[c],float):
                return jsonify(status="fail",message="Invalid vertex coordinates"),400
    if not isinstance(req["facets"],list):
        return jsonify(status="fail",message="Invalid facets list"),400
    for f in req["facets"]:
        if not isinstance(f,list):
            return jsonify(status="fail",message="Invalid facets"),400
        if not len(f) == 3:
            return jsonify(status="fail",message="Invalid facets"),400
        for i in range(3):
            if not isinstance(f[i],int):
                return jsonify(status="fail",message="Invalid facets"),400

    threed_dir = join(environ['OPENSHIFT_DATA_DIR'],'things',id,'3djs')
    if not exists(threed_dir):
        makedirs(threed_dir)
    filename = os.path.join(threed_dir,'threed.js')
    with open(filename,'w') as fid:
        fid.write(render_template('three.js',cam=req["camera"],vertices=req["vertices"],facets=req["facets"]))

    thing["3djs_file"] = 'threed.js'
    mongo.db.things.update({'_id' : id},thing)

    for t in mongo.db.thing.find({'_id' : id}):
        print t

    return jsonify(status='success')

@app.route('/3djs/<id>')
def download_3djs(id):
    thing = mongo.db.things.find_one({"_id" : id})
    if thing is None or not '3djs_file' in thing:
        abort(404)
    return send_file(join(environ['OPENSHIFT_DATA_DIR'],'things',id,'3djs',thing['3djs_file']),mimetype='text/javascript')





uuid_re = re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
def is_valid_uuid(uid):
    return not uuid_re.match(uid) is None

@app.route('/thing',methods=['POST'])
def add_thing():
    req = request.get_json()
    if not req:
        print "Bad request"
        abort(400)

    users = mongo.db.users
    if "token" in req:
        user = users.find_one({"token" : req["token"]})
        if user is None:
            print "Authentication failed"
            abort(403)
    else:
        print "Authentication failed"
        abort(403)

    if not "thing" in req:
        print "No thing supplied"
        abort(400)

    #TODO make sure only owner can overwrite things

    #sanitize thing TODO bleach
    thing = {}
    for key in ['id', 'title','description','license','license_url']:
        if not key in req["thing"]:
            abort(400)
        if key == 'id':
            if is_valid_uuid(req['thing']['id']):
                thing['_id'] = req["thing"]["id"]
            else:
                abort(400)
        else:
            thing[key] = req["thing"][key]
    thing['author'] = user['name']

    resp = {}
    resp['fcstd_url'] = urljoin(request.url,url_for('upload_fcstd',id=req['thing']['id']))
    resp['3djs_url'] = urljoin(request.url,url_for('upload_3djs',id=req['thing']['id']))

    things = mongo.db.things
    if things.find_one({'_id' : thing['_id']}) is None:
        things.insert(thing)
        resp['action'] = "created"
    else:
        things.update({'_id' : thing['_id']},thing)
        resp['action'] = "updated"

    return jsonify(**resp)

@app.route('/tracker')
def tracker():
    things = []
    for t in mongo.db.things.find():
        things.append({
            "id" : t["_id"],
            "url" : urljoin(request.url,url_for('show_thing',id=t["_id"])),
            "title" : t["title"],
            "authors" : [{"name" : t["author"]}],
            "description" : t["description"]
        })
    return render_template("tracker.json",things=things)

if __name__ == '__main__':

    app.run()
