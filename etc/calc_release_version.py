#!/usr/bin/env python

#
# Copyright 2018-present MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
A script that calculates the release version number (based on the current Git
branch and/or recent tags in history) to assign to a tarball generated from the
current Git commit.
"""

import datetime
import re
import sys
from distutils.version import LooseVersion
from git import Git, Repo # pip install GitPython

DEBUG = len(sys.argv) > 1 and '-d' in sys.argv
if DEBUG:
    print 'Debugging output enabled.'

RELEASE_TAG_RE = re.compile('r(?P<ver>(?P<vermaj>[0-9]+)\\.(?P<vermin>[0-9]+)'
                            '\\.(?P<verpatch>[0-9]+)(?:-(?P<verpre>.*))?)')
RELEASE_BRANCH_RE = re.compile('(?:origin/)?releases/v'
                               '(?P<vermaj>[0-9]+)\\.(?P<vermin>[0-9]+)')

def check_head_tag(repo):
    """
    Checks the current HEAD to see if it has been tagged with a tag that matches
    the pattern for a release tag.  Returns release version calculated from the
    tag, or None if there is no matching tag associated with HEAD.  If there are
    multiple release tags associated with HEAD, the one with the highest version
    is returned.
    """

    found_tag = False
    version_loose = LooseVersion('0.0.0')

    for tag in repo.tags:
        release_tag_match = RELEASE_TAG_RE.match(tag.name)
        if tag.commit == repo.head.commit and release_tag_match:
            new_version_loose = LooseVersion(release_tag_match.group('ver'))
            if new_version_loose > version_loose:
                if DEBUG:
                    print 'HEAD release tag: ' + release_tag_match.group('ver')
                version_loose = new_version_loose
                found_tag = True

    if found_tag:
        if DEBUG:
            print 'Calculated version: ' + str(version_loose)
        return str(version_loose)

    return None

def main():
    """
    The algorithm is roughly:

        1. Is the current HEAD associated with a tag that looks like a release
           version?
        2. If "yes" then use that as the version
        3. If "no" then is the current branch master?
        4. If "yes" the current branch is master, then inspect the branches that
           fit the convention for a release branch and choose the latest;
           increment the minor version, append .0 to form the new version (e.g.,
           releases/v3.3 becomes 3.4.0), and append a pre-release marker
        5. If "no" the current branch is not master, then determine the most
           recent tag in history; strip any pre-release marker, increment the
           patch version, and append a new pre-release marker
    """

    repo = Repo('.')
    assert not repo.bare

    head_tag_ver = check_head_tag(repo)
    if head_tag_ver:
        return head_tag_ver

    version_loose = LooseVersion('0.0.0')
    prerelease_marker = datetime.date.today().strftime('%Y%m%d') \
            + '+git' + repo.head.commit.hexsha[:10]

    if DEBUG:
        print 'Calculating release version for branch: ' + repo.active_branch.name
    if repo.active_branch.name == 'master':
        version_new = {}
        # Use refs (not branches) to get local branches plus remote branches
        for ref in repo.refs:
            release_branch_match = RELEASE_BRANCH_RE.match(ref.name)
            if release_branch_match:
                # Construct a candidate version from this branch name
                version_new['major'] = int(release_branch_match.group('vermaj'))
                version_new['minor'] = int(release_branch_match.group('vermin')) + 1
                version_new['patch'] = 0
                version_new['prerelease'] = prerelease_marker
                new_version_loose = LooseVersion(str(version_new['major']) + '.' +
                                                 str(version_new['minor']) + '.' +
                                                 str(version_new['patch']) + '-' +
                                                 version_new['prerelease'])
                if new_version_loose > version_loose:
                    version_loose = new_version_loose
                    if DEBUG:
                        print 'Found new best version "' + str(version_loose) \
                                + '" on branch "' + ref.name + '"'

    else:
        gexc = Git('.')
        tags = gexc.execute(['git', 'tag',
                             '--merged', 'HEAD',
                             '--list', 'r*',
                             '--sort', 'version:refname'])
        if len(tags) > 0:
            release_tag_match = RELEASE_TAG_RE.match(tags.splitlines()[-1])
            if release_tag_match:
                version_new = {}
                version_new['major'] = int(release_tag_match.group('vermaj'))
                version_new['minor'] = int(release_tag_match.group('vermin'))
                version_new['patch'] = int(release_tag_match.group('verpatch')) + 1
                version_new['prerelease'] = prerelease_marker
                new_version_loose = LooseVersion(str(version_new['major']) + '.' +
                                                 str(version_new['minor']) + '.' +
                                                 str(version_new['patch']) + '-' +
                                                 version_new['prerelease'])
                if new_version_loose > version_loose:
                    version_loose = new_version_loose
                    if DEBUG:
                        print 'Found new best version "' + str(version_loose) \
                                + '" from tag "' + release_tag_match.group('ver') + '"'

    return str(version_loose)

RELEASE_VER = main()
if DEBUG:
    print 'Final calculated release version:',
print RELEASE_VER