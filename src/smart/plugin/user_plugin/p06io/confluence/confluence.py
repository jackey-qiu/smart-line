
from __future__ import print_function
import json
import re
import requests
# a ConnectionError can be raise so catch that.

#fixme: todo
# create new table
# create table entry

# create list
# create list entry


##############
# confluence #
##############

class confluence(object):

    ############
    # __init__ #
    ############

    def __init__(self, space=None, verbosity=0):
        self.space = space
        self.verbosity = verbosity
        self._DESY_BASE_URL = 'https://confluence.desy.de/rest/api/content'
        self._HEADER = {'Content-Type': 'application/json'}
        self._communication = requests.Session()
        self._credentials = ('', '')

        self._PARAGRAPH = ['<p>', '</p>']
        self._HEADERS = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']

    # def _create_content_header_list(self, content):
    #     '''
    #     Converts the content string to a list.

    #     Parameters
    #     ----------
    #     content : str
    #         The page content string.

    #     Returns
    #     -------
    #     list
    #         List containing the split content.
    #     '''
    #     return re.findall('<.*?>', content)

    ########################
    # _create_content_list #
    ########################

    def _create_content_list(self, page_content):
        '''
        Creates a list from the page_content

        Parameters
        ----------
        page_content : str
            The page content string coming from the confluence restAPI.

        Returns
        -------
        list
            List containing the page content.
        '''

        content_list = re.split('(<.*?>)', page_content)

        while True:
            try:
                content_list.remove('')
            except ValueError:
                break

        return content_list


    # def _parse_page_content_to_dict(self, page_content):
    #     '''
    #     Converts the content of a page to a dictionary.

    #     Parameters
    #     ----------
    #     content : str
    #         The contents of a confluence page.
    #     '''

    #     headers = self._create_content_header_list(page_content)

    #     previous_header = None
    #     content_dict = {}
    #     bracket_remover = re.compile('^<|>$')
    #     for index, header in enumerate(headers):
    #         headers[index] = bracket_remover.sub(
    #             '',
    #             header,
    #             count=2
    #         )

    #     if self.verbosity > 3:
    #         print('Page headers: {}'.format(headers))

    #     content_list = self._create_content_list(page_content)

    #     # page_content_dict = self._create_content_dict(headers, content_list)
    #     header_tracking = []
    #     for index, header in enumerate(headers):
    #         if len(header_tracking) == 0:
    #             header_tracking.append(header)
    #         else:
    #             if header_tracking[-1] == ('/' + header):
    #                 header_tracking.pop(-1)
    #             else:
    #                 header_tracking.append(header)


    #     return page_content_dict

    ################################
    # _exchange_spaces_for_url_use #
    ################################

    def _exchange_spaces_for_url_use(self, string):
        '''
        Exchanges spaces with the url equivalent.
        '''

        return string.replace(' ', '%20')

    ########
    # _put #
    ########

    def _put(self, url, data):
        '''
        Sends the data to the url.

        Parameters
        ----------
        url : str
            The url to send the data to.

        data : dict
            The data to send to the url.
        '''

        self._communication.put(
            url,
            data=json.dumps(data),
            auth=self._credentials,
            headers=self._HEADER
        )

    ############
    # _request #
    ############

    def _request(self, url):
        '''
        Sends out a request to the url.

        Parameters
        ----------
        url : str
            The url to send the request to.

        Returns
        -------
        dict
            Dictionary containing the page's content.
        '''

        auth = self.get_auth()
        tmp = requests.get(url, auth=self._credentials)

        if tmp == '<Respons [401]':
            raise IOError('Unable to communicated (401)')

        if self.verbosity > 2:
            print(tmp)
        return tmp

    ############
    # get_auth #
    ############

    def get_auth(self):
        '''
        Gets the authentification.

        Returns
        -------
        tuple
            User name and password.
        '''

        return self._credentials

    #######################
    # _get_page_ancestors #
    #######################

    def _get_page_ancestors(self, page_id):
        '''
        Get the page ancestors.

        Parameters
        ----------
        page_id : int
            The page ID.

        Returns
        -------
        ?
            The page ancestors.
        '''

        url = str(
            self._DESY_BASE_URL
            + '/'
            + str(page_id)
            + '?expand=ancestors'
        )

        tmp = self._request(url)
        data = tmp.json()

        ancestors = [
            {
                'id': data['ancestors'][-1]['id'],
                'title': data['ancestors'][-1]['title'],
                'type': data['ancestors'][-1]['type']
            }
        ]

        return ancestors

    ########################
    # _get_page_id_by_name #
    ########################

    def _get_page_id_by_name(self, page_name, space_key=None):
        '''
        Gets the page ID by providing its name.

        Parameters
        ----------
        page_name : str
            The page name.

        space_key : str, optional
            The page key.

        Returns
        -------
        str
            The page ID.
        '''

        page_name = self._exchange_spaces_for_url_use(page_name)

        url = str(
            self._DESY_BASE_URL
            + '?title='
            + page_name
            + '&spaceKey='
            + self.space
            + '&expand=history'
        )

        tmp = self._request(url)

        return tmp.json()['results'][0]['id']

    ##################
    # _get_page_info #
    ##################

    def _get_page_info(self, page_id):
        '''
        Requests the page information.

        Parameters
        ----------
        page_id : int
            The page ID number.

        Returns
        -------
        dict
            Dictionary containing the page info.
        '''

        url = str(
            self._DESY_BASE_URL
            + '/'
            + page_id
        )

        return self._request(url).json()

    #####################
    # _get_page_version #
    #####################

    def _get_page_version(self, page_id, page_info=None):
        '''
        Retrieve the page version umber.

        Parmeters
        ---------
        page_id : int
            The page ID number.

        page_info : dict, optional
            The page info. Can be supplied when new page info does not need
            to be requested.

        Returns
        -------
        int
            The page version number.
        '''

        if page_info is None:
            page_info = self._get_page_info(page_id)

        return int(page_info['version']['number'])

    #####################
    # _get_page_content #
    #####################

    def _get_page_content(self, page_name):
        '''
        Retrieves the page content.

        Parameters
        ----------
        page_name : str
            The page name.

        Returns
        -------
        dict
            Dictionary containing the page content.
        '''

        page_id = self._get_page_id_by_name(page_name)

        if self.verbosity > 0:
            print('Page ID: {}'.format(page_id))

        url = str(
            self._DESY_BASE_URL
            + '/'
            + page_id
            + '?expand=body.storage'
        )

        return self._request(url).json()

    ####################
    # get_page_content #
    ####################

    def get_page_content(self, page_name):

        page_content = self._get_page_content(page_name)

        return self._create_content_list(
            page_content['body']['storage']['value']
        )

    ######################
    # write_page_content #
    ######################

    def write_page_content(self, page_name, page_content):
        '''
        Write new content to a confluence page.

        Parameters
        ----------
        page_name : str
            The page name.

        page_content : list
            The page content as a list.
        '''
        page_id = self._get_page_id_by_name(page_name)
        page_info = self._get_page_info(page_id)
        ancestors = self._get_page_ancestors(page_id)
        version = self._get_page_version(page_id, page_info=page_info)
        str_content = ''

        # Update page content
        page_info['body']['storage']['value'] = str_content.join(page_content)

        # Increment page version number.
        page_info['version']['number'] = version + 1

        # payload = {
        #     'id': page_id,
        #     'type': 'page',
        #     'title': page_name,
        #     'body': {
        #         'storage': {
        #             'value': str_content.join(page_content),
        #             'representation': 'storage'
        #         }
        #     },
        #     'version': {'number': version + 1},
        #     'ancestors': ancestors
        # }

        if self.verbosity > 2:
            print(page_info)

        url = str(
            self._DESY_BASE_URL
            + '/'
            + page_id
        )

        self._put(url, page_info)






## example reply
# {u'_links': {u'base': u'https://confluence.desy.de',
#   u'context': u'',
#   u'self': u'https://confluence.desy.de/rest/api/content?spaceKey=FSP06&expand=history&title=restAPI%20tests'},
#  u'limit': 25,
#  u'results': [{u'_expandable': {u'ancestors': u'',
#     u'body': u'',
#     u'children': u'/rest/api/content/120373944/child',
#     u'container': u'/rest/api/space/FSP06',
#     u'descendants': u'/rest/api/content/120373944/descendant',
#     u'metadata': u'',
#     u'operations': u'',
#     u'restrictions': u'/rest/api/content/120373944/restriction/byOperation',
#     u'space': u'/rest/api/space/FSP06',
#     u'version': u''},
#    u'_links': {u'edit': u'/pages/resumedraft.action?draftId=120373944&draftShareId=ebef8826-2384-4e2b-8cf1-66588724f216',
#     u'self': u'https://confluence.desy.de/rest/api/content/120373944',
#     u'tinyui': u'/x/uMIsBw',
#     u'webui': u'/display/FSP06/restAPI+tests'},
#    u'extensions': {u'position': u'none'},
#    u'history': {u'_expandable': {u'contributors': u'',
#      u'lastUpdated': u'',
#      u'nextVersion': u'',
#      u'previousVersion': u''},
#     u'_links': {u'self': u'https://confluence.desy.de/rest/api/content/120373944/history'},
#     u'createdBy': {u'_expandable': {u'status': u''},
#      u'_links': {u'self': u'https://confluence.desy.de/rest/api/user?key=032985584ed8d21c015060cc7b3c002f'},
#      u'displayName': u'Jan Garrevoet',
#      u'profilePicture': {u'height': 48,
#       u'isDefault': False,
#       u'path': u'/download/attachments/23489713/user-avatar',
#       u'width': 48},
#      u'type': u'known',
#      u'userKey': u'032985584ed8d21c015060cc7b3c002f',
#      u'username': u'garrej'},
#     u'createdDate': u'2019-02-18T22:16:42.245+01:00',
#     u'latest': True},
#    u'id': u'120373944',
#    u'status': u'current',
#    u'title': u'restAPI tests',
#    u'type': u'page'}],
#  u'size': 1,
#  u'start': 0}




# info get reply was

# {u'_expandable': {u'ancestors': u'',
#   u'body': u'',
#   u'children': u'/rest/api/content/89657480/child',
#   u'container': u'/rest/api/space/FSP06',
#   u'descendants': u'/rest/api/content/89657480/descendant',
#   u'metadata': u'',
#   u'operations': u'',
#   u'restrictions': u'/rest/api/content/89657480/restriction/byOperation'},
#  u'_links': {u'base': u'https://confluence.desy.de',
#   u'collection': u'/rest/api/content',
#   u'context': u'',
#   u'edit': u'/pages/resumedraft.action?draftId=89657480&draftShareId=cd6651bf-6335-4eca-a827-8e3ab5d0a036',
#   u'self': u'https://confluence.desy.de/rest/api/content/89657480',
#   u'tinyui': u'/x/iBBYBQ',
#   u'webui': u'/display/FSP06/User+Area'},
#  u'extensions': {u'position': 8},
#  u'history': {u'_expandable': {u'contributors': u'',
#    u'lastUpdated': u'',
#    u'nextVersion': u'',
#    u'previousVersion': u''},
#   u'_links': {u'self': u'https://confluence.desy.de/rest/api/content/89657480/history'},
#   u'createdBy': {u'_expandable': {u'status': u''},
#    u'_links': {u'self': u'https://confluence.desy.de/rest/api/user?key=032985584ed8d21c015060cc7b3c002f'},
#    u'displayName': u'Jan Garrevoet',
#    u'profilePicture': {u'height': 48,
#     u'isDefault': False,
#     u'path': u'/download/attachments/23489713/user-avatar',
#     u'width': 48},
#    u'type': u'known',
#    u'userKey': u'032985584ed8d21c015060cc7b3c002f',
#    u'username': u'garrej'},
#   u'createdDate': u'2018-04-13T14:18:05.737+02:00',
#   u'latest': True},
#  u'id': u'89657480',
#  u'space': {u'_expandable': {u'description': u'',
#    u'homepage': u'/rest/api/content/25440764',
#    u'icon': u'',
#    u'metadata': u''},
#   u'_links': {u'self': u'https://confluence.desy.de/rest/api/space/FSP06',
#    u'webui': u'/display/FSP06'},
#   u'id': 25722913,
#   u'key': u'FSP06',
#   u'name': u'FS-P06',
#   u'type': u'global'},
#  u'status': u'current',
#  u'title': u'User Area',
#  u'type': u'page',
#  u'version': {u'_expandable': {u'content': u'/rest/api/content/89657480'},
#   u'_links': {u'self': u'https://confluence.desy.de/rest/experimental/content/89657480/version/3'},
#   u'by': {u'_expandable': {u'status': u''},
#    u'_links': {u'self': u'https://confluence.desy.de/rest/api/user?key=032985584ed8d21c015060cc7b3c002f'},
#    u'displayName': u'Jan Garrevoet',
#    u'profilePicture': {u'height': 48,
#     u'isDefault': False,
#     u'path': u'/download/attachments/23489713/user-avatar',
#     u'width': 48},
#    u'type': u'known',
#    u'userKey': u'032985584ed8d21c015060cc7b3c002f',
#    u'username': u'garrej'},
#   u'hidden': False,
#   u'message': u'',
#   u'minorEdit': False,
#   u'number': 3,
#   u'when': u'2018-04-13T15:55:13.152+02:00'}}



# content reply was

# {u'_expandable': {u'ancestors': u'',
#   u'children': u'/rest/api/content/118292278/child',
#   u'container': u'/rest/api/space/FSP06',
#   u'descendants': u'/rest/api/content/118292278/descendant',
#   u'history': u'/rest/api/content/118292278/history',
#   u'metadata': u'',
#   u'operations': u'',
#   u'restrictions': u'/rest/api/content/118292278/restriction/byOperation',
#   u'space': u'/rest/api/space/FSP06',
#   u'version': u''},
#  u'_links': {u'base': u'https://confluence.desy.de',
#   u'collection': u'/rest/api/content',
#   u'context': u'',
#   u'edit': u'/pages/resumedraft.action?draftId=118292278',
#   u'self': u'https://confluence.desy.de/rest/api/content/118292278',
#   u'tinyui': u'/x/Nv8MBw',
#   u'webui': u'/pages/viewpage.action?pageId=118292278'},
#  u'body': {u'_expandable': {u'anonymous_export_view': u'',
#    u'editor': u'',
#    u'export_view': u'',
#    u'styled_view': u'',
#    u'view': u''},
#   u'storage': {u'_expandable': {u'content': u'/rest/api/content/118292278'},
#    u'representation': u'storage',
#    u'value': u'<h2>Attendees:</h2><ul><li>&nbsp;</li></ul><h2>Discussion Items:</h2><table class='relative-table wrapped' style='width: 50.4348%;'><colgroup><col style='width: 25.6472%;' /><col style='width: 20.9079%;' /><col style='width: 53.443%;' /></colgroup><tbody><tr><th>Item</th><th>Who</th><th>Notes</th></tr><tr><td><ul><li>Meta-data Server</li></ul></td><td><div class='content-wrapper'><ul><li><ac:link><ri:user ri:userkey='032985584ed8d21c015060cc7b3c002f' /><ac:plain-text-link-body><![CDATA[Jan]]></ac:plain-text-link-body></ac:link></li></ul></div></td><td><ul><li>The metadata server is not a hidden service anymore but is now a tango server. General docs are <ac:link><ri:page ri:content-title='Software Control' /><ac:plain-text-link-body><![CDATA[HERE]]></ac:plain-text-link-body></ac:link>.</li><li>Normally interaction with it should not be necessary.</li><li>Main thing is that it now also starts when the pc boots.</li></ul></td></tr><tr><td><ul><li>Eiger maintenance</li></ul></td><td><div class='content-wrapper'><ul><li><ac:link><ri:user ri:userkey='032985584ed8d21c015060cc7b3c002f' /><ac:plain-text-link-body><![CDATA[Jan]]></ac:plain-text-link-body></ac:link></li></ul></div></td><td><div class='content-wrapper'><ul><li>Will be done on <time datetime='2019-02-19' /></li></ul></div></td></tr><tr><td><ul><li>P05 SE</li></ul></td><td><ul><li><ac:link><ri:user ri:userkey='032985585fe2ff040160d67909d5006e' /></ac:link></li></ul></td><td><ul><li>Nicole von Bargen informed me that HZG (P05) will keep on using Solid Edge. However we should have a current version of their beamline available in our NX model. We should talk to the P05 staff.</li></ul></td></tr><tr><td colspan='1'><ul><li>new KB chamber</li></ul></td><td colspan='1'><ul><li><ac:link><ri:user ri:userkey='032984bc48e9b9d50149aeec737e0025' /></ac:link></li></ul></td><td colspan='1'><ul><li>the budget for the new KB chamber should at least be touched already this year. Otherwise there is the risk of decline. In conclusion: the design of the KB chamber has high(est) priority!</li></ul></td></tr><tr><td colspan='1'><ul><li>4 BMBF proposals</li></ul></td><td colspan='1'><ul><li><ac:link><ri:user ri:userkey='032984bc48e9b9d50149aeec737e0025' /></ac:link></li></ul></td><td colspan='1'><ul><li>there are 4 BMBF proposals for P06 currently reviewed:<br /><ul><li>Sheppard/Grunwaldt: in-operando catalyst research</li><li>Kipp: Time resolved XEOL</li><li>Rosenhahn: Cryochamber</li><li>Geck: bulk-sensitive magnetic imaging</li></ul></li></ul></td></tr><tr><td colspan='1'><ul><li>rotation stage</li></ul></td><td colspan='1'><ul><li><ac:link><ri:user ri:userkey='032984bc48e9b9d50149aeec737e0025' /></ac:link></li></ul></td><td colspan='1'><ul><li>NanoMax beamline is also looking for a solution. They consider a solution from smaract: 70-100 mm rotary stage with ceramic bearings (lightweight).</li></ul></td></tr><tr><td colspan='1'><ul><li>Vacuum system</li></ul></td><td colspan='1'><div class='content-wrapper'><ul><li><ac:link><ri:user ri:userkey='032985584ed8d21c015060cc7b3c002f' /></ac:link></li></ul></div></td><td colspan='1'><ul><li>The pipe going to EH2 has been modified to allow:<ul><li>Easier connect to the flight tube in EH2.</li><li>Allow for a separation between EH1 and EH2 at the pump side.</li><li>Put 2 pumps in parallel.</li><li>Put pumps to 1 single branch.</li><li>test_api</li></ul></li></ul></td></tr></tbody></table><p><br /></p><p><br /></p><p><br /></p>'}},
#  u'extensions': {u'position': u'none'},
#  u'id': u'118292278',
#  u'status': u'current',
#  u'title': u'2019-02-?? Group Meeting',
#  u'type': u'page'}






## when there is an issue:

# {u'data': {u'allowedInReadOnlyMode': True,
#   u'authorized': False,
#   u'errors': [],
#   u'successful': False,
#   u'valid': True},
#  u'message': u'No space with key : FS-P06',
#  u'reason': u'Not Found',
#  u'statusCode': 404}




## beamtime template

# {u'_expandable': {u'ancestors': u'',
#   u'children': u'/rest/api/content/120373944/child',
#   u'container': u'/rest/api/space/FSP06',
#   u'descendants': u'/rest/api/content/120373944/descendant',
#   u'history': u'/rest/api/content/120373944/history',
#   u'metadata': u'',
#   u'operations': u'',
#   u'restrictions': u'/rest/api/content/120373944/restriction/byOperation',
#   u'space': u'/rest/api/space/FSP06',
#   u'version': u''},
#  u'_links': {u'base': u'https://confluence.desy.de',
#   u'collection': u'/rest/api/content',
#   u'context': u'',
#   u'edit': u'/pages/resumedraft.action?draftId=120373944&draftShareId=ebef8826-2384-4e2b-8cf1-66588724f216',
#   u'self': u'https://confluence.desy.de/rest/api/content/120373944',
#   u'tinyui': u'/x/uMIsBw',
#   u'webui': u'/display/FSP06/RESTapi'},
#  u'body': {u'_expandable': {u'anonymous_export_view': u'',
#    u'editor': u'',
#    u'export_view': u'',
#    u'styled_view': u'',
#    u'view': u''},
#   u'storage': {u'_expandable': {u'content': u'/rest/api/content/120373944'},
#    u'representation': u'storage',
#    u'value': u'<h1>General</h1><h2>Beamtime Parameters</h2><ul><li>Beamtime ID:&nbsp;</li><li>Start date:&nbsp;<time datetime="2019-04-27" /></li><li>End date:&nbsp;<time datetime="2019-04-30" /></li><li>Primary beam energy: 16 keV</li><li>Used detectors:<ul><li>Maia</li><li>Vortex</li><li>Eiger 4M</li></ul></li></ul><h1>Measurements</h1><h2>Alignment</h2><table class="wrapped"><colgroup><col /><col /><col /><col /></colgroup><tbody><tr><th>Scan #</th><th>Scan Command</th><th>Info</th><th>Thumbnail</th></tr><tr><td>1</td><td>cnt</td><td><br /></td><td><br /></td></tr><tr><td>2</td><td>dscan samy 0 1 10 0.1</td><td><ul><li>Info test</li></ul></td><td><div class="content-wrapper"><p><ac:image ac:thumbnail="true" ac:height="150"><ri:attachment ri:filename="DESY_Luftbild_mit_Beschleunigern_RS-0045_a 16-9.jpg" /></ac:image></p></div></td></tr></tbody></table>'}},
#  u'extensions': {u'position': u'none'},
#  u'id': u'120373944',
#  u'status': u'current',
#  u'title': u'RESTapi',
#  u'type': u'page'}


