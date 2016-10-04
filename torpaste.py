#!bin/python
# -*- coding: utf-8 -*-

import importlib
import time
from datetime import datetime
from hashlib import sha256
from os import getenv

from flask import *

app = Flask(__name__)

VERSION = "0.5"
COMPATIBLE_BACKENDS = ["filesystem"]


@app.route('/')
def index():
    return render_template(
        "index.html",
        title=WEBSITE_TITLE,
        version=VERSION,
        page="main"
    )


@app.route("/new", methods=["GET", "POST"])
def new_paste():
    if request.method == "GET":
        return render_template(
            "index.html",
            title=WEBSITE_TITLE,
            version=VERSION,
            page="new"
        )
    else:
        if request.form['content']:
            try:
                paste_id = str(sha256(request.form['content'].encode('utf-8')).hexdigest())
            except:
                return render_template(
                    "index.html",
                    title=WEBSITE_TITLE,
                    version=VERSION,
                    page="new",
                    error="An issue occurred while handling the paste. Please try again later. If the problem persists,\
                     try notifying a system administrator."
                )

            if len(request.form['content'].encode('utf-8')) > MAX_PASTE_SIZE:
                return render_template(
                    "index.html",
                    title=WEBSITE_TITLE,
                    version=VERSION,
                    page="new",
                    error="The paste sent is too large. This TorPaste instance has a maximum allowed paste size of "
                          + format_size(MAX_PASTE_SIZE) + "."
                )

            try:
                b.new_paste(paste_id, request.form['content'])
            except b.e.ErrorException as errmsg:
                return render_template(
                    "index.html",
                    title=WEBSITE_TITLE,
                    version=VERSION,
                    page="new",
                    error=errmsg
                )

            try:
                b.update_paste_metadata(
                    paste_id,
                    {
                        "date": unicode(int(time.time()))
                    }
                )
            except b.e.ErrorException as errmsg:
                return render_template(
                    "index.html",
                    title=WEBSITE_TITLE,
                    version=VERSION,
                    page="new",
                    error=errmsg
                )

            return redirect("/view/" + paste_id)
        else:
            return Response(
                render_template(
                    "index.html",
                    title=WEBSITE_TITLE,
                    version=VERSION,
                    error="Please enter some text to include in the paste.",
                    page="new"
                ),
                400
            )


@app.route("/view/<pasteid>")
def view_paste(pasteid):
    if not pasteid.isalnum():
        return Response(
            render_template(
                "index.html",
                title=WEBSITE_TITLE,
                version=VERSION,
                error="Invalid Paste ID. Please check the link you used or use Pastes button above.",
                page="new"
            ),
            400
        )
    if len(pasteid) < 6:
        return Response(
            render_template(
                "index.html",
                title=WEBSITE_TITLE,
                version=VERSION,
                error="Paste ID too short. Usually Paste IDs are longer than 6 characters. Please make sure the link \
                you clicked is correct or use the Pastes button above.",
                page="new"
            ),
            400
        )
    if not b.does_paste_exist(pasteid):
        return Response(
            render_template(
                "index.html",
                title=WEBSITE_TITLE,
                version=VERSION,
                error="A paste with this ID could not be found. Sorry.",
                page="new"
            ),
            404
        )

    try:
        paste_content = b.get_paste_contents(pasteid)
    except b.e.ErrorException as errmsg:
        return render_template(
            "index.html",
            title=WEBSITE_TITLE,
            version=VERSION,
            error=errmsg,
            page="new"
        )

    try:
        paste_date = b.get_paste_metadata_value(pasteid, "date")
    except b.e.ErrorException as errmsg:
        return render_template(
            "index.html",
            title=WEBSITE_TITLE,
            version=VERSION,
            error=errmsg,
            page="new"
        )
    except b.e.WarningException as errmsg:
        return render_template(
            "index.html",
            title=WEBSITE_TITLE,
            version=VERSION,
            warning=errmsg,
            page="new"
        )

    paste_date = datetime.fromtimestamp(int(paste_date) + time.altzone + 3600).strftime("%H:%M:%S %d/%m/%Y")
    paste_size = format_size(len(paste_content.encode('utf-8')))
    return render_template(
        "view.html",
        content=paste_content,
        date=paste_date,
        size=paste_size,
        pid=pasteid,
        title=WEBSITE_TITLE,
        version=VERSION,
        page="view"
    )


@app.route("/raw/<pasteid>")
def raw_paste(pasteid):
    if not pasteid.isalnum():
        return "No such paste", 404
    if len(pasteid) < 6:
        return "No such paste", 404
    if not b.does_paste_exist(pasteid):
        return "No such paste", 404
    try:
        paste_content = b.get_paste_contents(pasteid)
    except b.e.ErrorException as errmsg:
        return Response(
            errmsg,
            500
        )
    return Response(
        paste_content,
        mimetype="text/plain"
    )


@app.route("/list")
def list():
    try:
        paste_list = b.get_all_paste_ids()
    except b.e.ErrorException as errmsg:
        return render_template(
            "index.html",
            title=WEBSITE_TITLE,
            version=VERSION,
            page="new",
            error=errmsg
        )

    if paste_list[0] == 'none':
        return render_template(
            "list.html",
            pastes=['none'],
            title=WEBSITE_TITLE,
            version=VERSION,
            page="list"
        )
    return render_template(
        "list.html",
        pastes=paste_list,
        title=WEBSITE_TITLE,
        version=VERSION,
        page="list"
    )


@app.route("/about")
def about_tor_paste():
    return render_template(
        "about.html",
        title=WEBSITE_TITLE,
        version=VERSION,
        page="about"
    )


# Functions
def format_size(size):
    scales = ["bytes", "kB", "MB", "GB", "TB", "PB"]
    count = 0
    while 1 == 1:
        if size > 1024.0:
            size /= 1024.0
            count += 1
        else:
            break
    return str(round(size, 1)) + " " + scales[count]


# Required Initialization Code
# Handle Environment Variables (for configuration)
# Web App <title>
WEBSITE_TITLE = getenv("TP_WEBSITE_TITLE") or "Tor Paste"

# Backend Used
BACKEND = getenv("TP_BACKEND") or "filesystem"

if BACKEND in COMPATIBLE_BACKENDS:
    b = importlib.import_module('backends.' + BACKEND)
else:
    print("Configured backend (" + BACKEND + ") is not compatible with current version.")
    exit(1)

# Maximum Paste Size
MAX_PASTE_SIZE = getenv("TP_PASTE_MAX_SIZE") or "1 P"

if MAX_PASTE_SIZE[0] == "0":
    MAX_PASTE_SIZE = "1 P"

MAX_PASTE_SIZE = MAX_PASTE_SIZE.split(" ")

try:
    AMOUNT = int(MAX_PASTE_SIZE[0])
    UNIT = MAX_PASTE_SIZE[1]
except:
    print("Invalid TP_PASTE_MAX_SIZE: " + " ".join(MAX_PASTE_SIZE))
    exit(1)

orders = ["B", "k", "M", "G", "T", "P"]

if UNIT not in orders:
    print("Invalid Unit Size: " + UNIT)

try:
    MAX_PASTE_SIZE = AMOUNT * 1024 ** orders.index(UNIT)
except:
    print("An unknown error occurred while determining max paste size.")
    exit(1)

# Initialize Backend
try:
    b.initialize_backend()
except:
    print("Failed to initialize backend")
    exit(1)

if __name__ == '__main__':
    app.run(host="0.0.0.0")
