r"""
==============
GitHub Formatter
==============

This formatter outputs the issues as plain text.

:Example:

.. code-block:: none

    >> Issue: [B301:blacklist_calls] Use of unsafe yaml load. Allows
       instantiation of arbitrary objects. Consider yaml.safe_load().

       Severity: Medium   Confidence: High
       Location: examples/yaml_load.py:5
       More Info: https://bandit.readthedocs.io/en/latest/
    4       ystr = yaml.dump({'a' : 1, 'b' : 2, 'c' : 3})
    5       y = yaml.load(ystr)
    6       yaml.dump(y)

.. versionadded:: 0.9.0

"""

from __future__ import print_function

import logging
import json
import os

import requests
from bandit.core import constants
from bandit.core import docs_utils
from bandit.core import test_properties

LOG = logging.getLogger(__name__)


def get_verbose_details(manager):
    # TODO: re-format the output for verbose details
    bits = []
    bits.append(u'Files in scope (%i):' % len(manager.files_list))
    tpl = u"\t%s (score: {SEVERITY: %i, CONFIDENCE: %i})"
    bits.extend([tpl % (item, sum(score['SEVERITY']), sum(score['CONFIDENCE']))
                 for (item, score)
                 in zip(manager.files_list, manager.scores)])
    bits.append(u'Files excluded (%i):' % len(manager.excluded_files))
    bits.extend([u"\t%s" % fname for fname in manager.excluded_files])
    return '\n'.join([bit for bit in bits])


def get_metrics(manager):
    bits = []
    bits.append("\n### Run metrics:\n")
    bits.append(f"| | {'|'.join(constants.RANKING)}|")
    bits.append("|:-:|:-:|:-:|:-:|:-:|")
    severity_list = [str(int(manager.metrics.data['_totals'][f'SEVERITY.{rank}'])) for rank in constants.RANKING]
    bits.append(f"|SEVERITY|{'|'.join(severity_list)}|")
    confidence_list = [str(int(manager.metrics.data['_totals'][f'CONFIDENCE.{rank}'])) for rank in constants.RANKING]
    bits.append(f"|CONFIDENCE|{'|'.join(confidence_list)}|")
    return '\n'.join([bit for bit in bits])


def _output_issue_str(issue, indent, show_lineno=True, show_code=True,
                      lines=-1):
    # returns a list of lines that should be added to the existing lines list
    bits = []
    bits.append("<details>")
    bits.append("<summary><strong>[%s:%s]</strong> %s</summary>\n<br>\n" % (
        issue.test_id, issue.test, issue.text))

    bits.append("|<strong>Severity</strong>| %s |\n|:-:|:-:|\n|<strong>Confidence</strong>| %s |" % (
        issue.severity.capitalize(), issue.confidence.capitalize()))

    bits.append("|<strong>Location<strong>| %s:%s:%s |" % (
        issue.fname, issue.lineno if show_lineno else "",
        ""))

    bits.append("|<strong>More Info<strong>| %s |\n" % (
        docs_utils.get_url(issue.test_id)))

    if show_code:
        bits.append("<br>\n\n```python")
        bits.extend([indent + line for line in
                     issue.get_code(lines, True).split('\n')])
        bits.append("```\n")

    bits.append("</details>")
    return '\n'.join([bit for bit in bits])


def get_results(manager, sev_level, conf_level, lines):
    bits = []
    issues = manager.get_issue_list(sev_level, conf_level)
    baseline = not isinstance(issues, list)
    candidate_indent = ' ' * 10

    if not len(issues):
        return u"\tNo issues identified."

    for issue in issues:
        # if not a baseline or only one candidate we know the issue
        if not baseline or len(issues[issue]) == 1:
            bits.append(_output_issue_str(issue, "", lines=lines))

        # otherwise show the finding and the candidates
        else:
            bits.append(_output_issue_str(issue, "",
                                          show_lineno=False,
                                          show_code=False))

            bits.append(u'\n-- Candidate Issues --')
            for candidate in issues[issue]:
                bits.append(_output_issue_str(candidate,
                                              candidate_indent,
                                              lines=lines))
                bits.append('\n')
    return '\n'.join([bit for bit in bits])


def comment_on_pr(message):

    token = os.getenv("INPUT_GITHUB_TOKEN")
    if not token:
        print(message)
        return

    if os.getenv("GITHUB_EVENT_NAME") == "pull_request":
        with open(os.getenv("GITHUB_EVENT_PATH")) as json_file:
            event = json.load(json_file)
            headers_dict = {
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {token}"
            }

            request_path = (
                f"https://api.github.com/repos/{event['repository']['full_name']}/issues/{event['number']}/comments")

            requests.post(request_path, headers=headers_dict, json={"body": message})


@test_properties.accepts_baseline
def report(manager, fileobj, sev_level, conf_level, lines=-1):
    """Prints discovered issues in the text format

    :param manager: the bandit manager object
    :param fileobj: The output file object, which may be sys.stdout
    :param sev_level: Filtering severity level
    :param conf_level: Filtering confidence level
    :param lines: Number of lines to report, -1 for all
    """
    bits = []
    if manager.results_count(sev_level, conf_level):

        if manager.verbose:
            bits.append(get_verbose_details(manager))

        bits.append("## Bandit results:")

        bits.append('<strong>Total lines of code:</strong> %i' %
                    (manager.metrics.data['_totals']['loc']))

        bits.append('<strong>Total lines skipped (#nosec):</strong> %i' %
                    (manager.metrics.data['_totals']['nosec']))

        bits.append(get_metrics(manager))

        bits.append("<details><summary>📋 Click here to see the all possible security issues</summary>\n<br>\n")
        bits.append(get_results(manager, sev_level, conf_level, lines))
        bits.append("</details>")

        result = '\n'.join([bit for bit in bits]) + '\n'

        comment_on_pr(result)
