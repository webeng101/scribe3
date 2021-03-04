from flask import Flask, escape, request, jsonify
import json
from cli import cli

app = Flask('Scribe3 web api')

@app.route('/<expression>')
def command(expression):
    try:
        tokens = cli.tokenize(expression)
        command, args = cli.lex(tokens)
        res = cli.evaluate(command, args)
        ret = jsonify(res)
    except Exception as e:
        ret = jsonify(str(e))
    return ret