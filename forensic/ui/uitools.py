'''
Copyright 2013 Hannu Visti

This file is part of ForGe forensic test image generator.
ForGe is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with ForGe.  If not, see <http://www.gnu.org/licenses/>.
'''

from subprocess import call
import sys

HELPER = "/home/forensic/chelper"



def errlog(message):
    print >>sys.stderr, message

class ForensicError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
