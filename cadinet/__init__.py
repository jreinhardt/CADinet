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

from flask import Flask, render_template, request, flash, redirect, url_for, g, abort, jsonify, send_file, current_app, Response
from flask.ext.pymongo import PyMongo
from flask_wtf import Form
from wtforms import TextField
from wtforms.validators import DataRequired, URL, Email, Regexp
from werkzeug import secure_filename
from functools import wraps

from urlparse import urljoin

import json
import jsonschema
import cPickle

from os import environ, mkdir, makedirs, getenv
from os.path import exists,join
from shutil import rmtree
import os.path
import sys
import logging
from logging.handlers import RotatingFileHandler
import random
import re

from hashlib import sha1

import bleach

LICENSES = {
    "CC0 1.0" : "http://creativecommons.org/publicdomain/zero/1.0/",
    "CC-BY 3.0" : "http://creativecommons.org/licenses/by/3.0/",
    "CC-BY 4.0" : "http://creativecommons.org/licenses/by/4.0/",
    "CC-BY-SA 4.0" : "http://creativecommons.org/licenses/by-sa/4.0/",
    "CC-BY-ND 4.0" : "http://creativecommons.org/licenses/by-nd/4.0/",
    "CC-BY-NC 4.0" : "http://creativecommons.org/licenses/by-nc/4.0/",
    "CC-BY-NC-SA 4.0" : "http://creativecommons.org/licenses/by-nc-sa/4.0/",
    "CC-BY-NC-ND 4.0" : "http://creativecommons.org/licenses/by-nc-nd/4.0/",
    "MIT" : "http://opensource.org/licenses/MIT", #see https://fedoraproject.org/wiki/Licensing:MIT?rd=Licensing/MIT
    "BSD 3-clause" : "http://opensource.org/licenses/BSD-3-Clause",
    "Apache 2.0" : "http://www.apache.org/licenses/LICENSE-2.0",
    "LGPL 2.1" : "http://www.gnu.org/licenses/lgpl-2.1",
    "LGPL 2.1+" : "http://www.gnu.org/licenses/lgpl-2.1",
    "LGPL 3.0" : "http://www.gnu.org/licenses/lgpl-3.0",
    "LGPL 3.0+" : "http://www.gnu.org/licenses/lgpl-3.0",
    "GPL 2.0+" : "http://www.gnu.org/licenses/gpl-2.0",
    "GPL 3.0" : "http://www.gnu.org/licenses/gpl-3.0",
    "GPL 3.0+" : "http://www.gnu.org/licenses/gpl-3.0",
}


app = Flask(__name__)
app.config['ENABLE_REGISTRATION'] = True
app.config['SSL'] = True

#mongodb defaults
app.config['MONGO_HOST'] = getenv("OPENSHIFT_MONGODB_DB_HOST",None)
app.config['MONGO_PORT'] = getenv("OPENSHIFT_MONGODB_DB_PORT",None)
app.config['MONGO_USERNAME'] = getenv("OPENSHIFT_MONGODB_DB_USERNAME",None)
app.config['MONGO_PASSWORD'] = getenv("OPENSHIFT_MONGODB_DB_PASSWORD",None)

app.config.from_pyfile(join(environ['OPENSHIFT_DATA_DIR'],'cadinet.cfg'))

mongo = PyMongo(app)

spec_dir = join(app.root_path,'specs')
def validate(instance,filename):
    if not instance:
        return jsonify(status="fail",message="There was a problem with the request"),400
    try:
        schema = json.loads(open(join(spec_dir,filename)).read())
        jsonschema.validate(instance,schema)
    except jsonschema.SchemaError as e:
        app.logger.error("SchemaError: " + e.message)
        return jsonify(status="fail",message="Invalid schema. This is not your fault, please report a bug"), 400
    except jsonschema.ValidationError as e:
        app.logger.error("ValidationError: " + e.message)
        return jsonify(status="fail",message=e.message), 400
    else:
        return None

log_handler = RotatingFileHandler(join(environ['OPENSHIFT_LOG_DIR'],'cadinet.log'),maxBytes=2**20,backupCount=3)
log_handler.setLevel(logging.INFO)
log_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'
))

app.logger.addHandler(log_handler)
logging.getLogger().addHandler(log_handler)

uuid_re = re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
def is_valid_uuid(uid):
    return not uuid_re.match(uid) is None

def ssl_required(fn):
    @wraps(fn)
    def decorated_view(*args, **kwargs):
        if current_app.config.get("SSL"):
            if request.is_secure:
                return fn(*args, **kwargs)
            else:
                return redirect(request.url.replace("http://", "https://"))
        return fn(*args, **kwargs)
    return decorated_view

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    user = mongo.db.users.find_one({'_id' : username})
    if user is None:
        return False

    return sha1(password).hexdigest() == user['password_hash']

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

class CredentialsForm(Form):
    username = TextField("username",validators=[DataRequired(),Regexp('[a-zA-Z0-9_-]{6,30}',
        message="Username must only contain alphanumerical characters and _-")]
    )
    email = TextField("email",validators=[DataRequired()])

class SubmissionForm(Form):
    url = TextField("url",validators=[DataRequired(),URL(require_tld=True)])

class SearchForm(Form):
    query = TextField("query",validators=[DataRequired()])


@app.route('/')
def home():
    return redirect(url_for("about"))

@app.route('/about')
def about():
    return render_template('about.html',licenses = LICENSES.items())

@app.route('/register',methods=['GET','POST'])
@ssl_required
def register():
    if not app.config['ENABLE_REGISTRATION']:
        abort(404)
    form = CredentialsForm()
    if form.validate_on_submit():
        users = mongo.db.users
        if not users.find_one({'_id' : form.username.data}) is None:
            flash('Username already exists, please choose a different one')
            return render_template('register.html',form = form)

        password = "%x" % random.SystemRandom().getrandbits(64)

        user = {
            '_id' : form.username.data,
            'email' : form.email.data,
            #for a random password no salt is necessary
            'password_hash' : sha1(password).hexdigest()
        }
        users.insert(user)
        return render_template('token.html',username = form.username.data, password=password)

    return render_template('register.html', form = form)

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
           filename.rsplit('.', 1)[1].lower() in exts

@app.route('/upload/fcstd/<id>',methods=['POST'])
@ssl_required
@auth_required
def upload_fcstd(id):
    thing = mongo.db.things.find_one({"_id" : id})
    if thing is None:
        return jsonify(status="fail",message="No thing with ID %s found" % id),404
    elif request.authorization.username != thing["author"]:
        return jsonify(status="fail",message="You are not allowed to update this thing"),403

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
    return send_file(join(environ['OPENSHIFT_DATA_DIR'],'things',id,'fcstd',thing['fcstd_file']),
            mimetype='application/x-extension-fcstd',
            as_attachment=True,
            attachment_filename=os.path.basename(thing['fcstd_file']))

@app.route('/upload/3dview/<id>',methods=['POST'])
@ssl_required
@auth_required
def upload_3dview(id):
    thing = mongo.db.things.find_one({"_id" : id})
    if thing is None:
        return jsonify(status="fail",message="No thing with ID %s found" % id),404
    elif request.authorization.username != thing["author"]:
        return jsonify(status="fail",message="You are not allowed to update this thing"),403

    req = request.get_json()


    threed_dir = join(environ['OPENSHIFT_DATA_DIR'],'things',id,'3dview')
    if not exists(threed_dir):
        makedirs(threed_dir)
    filename = os.path.join(threed_dir,'threed.dat')

    with open(filename,'w') as fid:
        pick = cPickle.Pickler(fid)
        pick.dump(req)

    thing["3d_dat"] = 'threed.dat'
    mongo.db.things.update({'_id' : id},thing)

    for t in mongo.db.thing.find({'_id' : id}):
        print t

    return jsonify(status='success')

@app.route('/3djs/<id>')
def download_3djs(id):
    thing = mongo.db.things.find_one({"_id" : id})
    if thing is None or not '3d_dat' in thing:
        abort(404)

    with open(join(environ['OPENSHIFT_DATA_DIR'],'things',id,'3dview',thing['3d_dat'])) as fid:
        upick = cPickle.Unpickler(fid)
        req = upick.load()

    return render_template('three.js',cam=req["camera"],vertices=req["vertices"],facets=req["facets"])

@app.route('/thing',methods=['POST'])
@ssl_required
@auth_required
def add_thing():
    req = request.get_json()

    users = mongo.db.users
    user = users.find_one({"_id" : request.authorization.username})

    thing = {}

    if is_valid_uuid(req['thing']['id']):
        thing['_id'] = req["thing"]["id"]
    else:
        return jsonify(status="fail",message="Invalid thing id"),400

    #sanitize thing
    for key in ['title','description','license','license_url']:
        thing[key] = bleach.clean(req["thing"][key],strip=True)
    thing['author'] = user['_id']

    if not thing['license'] in LICENSES or LICENSES[thing['license']] != thing['license_url']:
        return jsonify(status="fail",message="License not allowed or unknown license url, see %s for more information" % url_for('about'))

    resp = {}
    resp['fcstd_url'] = urljoin(request.url,url_for('upload_fcstd',id=req['thing']['id']))
    resp['3dview_url'] = urljoin(request.url,url_for('upload_3dview',id=req['thing']['id']))

    things = mongo.db.things
    thing_ex = things.find_one({'_id' : thing['_id']})
    if thing_ex is None:
        things.insert(thing)
        resp["status"] = "created"
    else:
        #make sure only owner can overwrite things
        if request.authorization.username != thing_ex["author"]:
            return jsonify(status="fail",message="You are not allowed to update this thing"),403

        things.update({'_id' : thing['_id']},thing)
        resp["status"] = "updated"

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

@app.route('/tracker/<user>')
def tracker_user(user):
    things = []
    for t in mongo.db.things.find({'author' : user}):
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
