try:
    import ldap as _ldap
    from .ldap_query import LdapQuery
except ImportError:
    pass

from .ldap_search import LdapSearch
