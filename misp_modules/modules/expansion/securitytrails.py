import json
import logging
import sys
import time

from dnstrails import APIError
from dnstrails import DnsTrails

log = logging.getLogger('dnstrails')
log.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
log.addHandler(ch)

misperrors = {'error': 'Error'}
mispattributes = {
    'input': ['hostname', 'domain', 'ip-src', 'ip-dst'],
    'output': ['hostname', 'domain', 'ip-src', 'ip-dst', 'dns-soa-email',
               'whois-registrant-email', 'whois-registrant-phone',
               'whois-registrant-name',
               'whois-registrar', 'whois-creation-date', 'domain']
}

moduleinfo = {'version': '1', 'author': 'Sebastien Larinier @sebdraven',
              'description': 'Query on securitytrails.com',
              'module-type': ['expansion', 'hover']}

# config fields that your code expects from the site admin
moduleconfig = ['apikey']


def handler(q=False):
    if q:

        request = json.loads(q)

        if not request.get('config') and not (request['config'].get('apikey')):
            misperrors['error'] = 'DNS authentication is missing'
            return misperrors

        api = DnsTrails(request['config'].get('apikey'))

        if not api:
            misperrors['error'] = 'Onyphe Error instance api'

        ip = ""
        dns_name = ""

        ip = ''
        if request.get('ip-src'):
            ip = request['ip-src']
            return handle_ip(api, ip, misperrors)
        elif request.get('ip-dst'):
            ip = request['ip-dst']
            return handle_ip(api, ip, misperrors)
        elif request.get('domain'):
            domain = request['domain']
            return handle_domain(api, domain, misperrors)
        elif request.get('hostname'):
            hostname = request['hostname']
            return handle_domain(api, hostname, misperrors)
        else:
            misperrors['error'] = "Unsupported attributes types"
            return misperrors
    else:
        return False


def handle_domain(api, domain, misperrors):
    result_filtered = {"results": []}

    r, status_ok = expand_domain_info(api, misperrors, domain)
    #
    if status_ok:
        if r:
            result_filtered['results'].extend(r)
    else:
        misperrors['error'] = misperrors['error'] + ' Error DNS result'
        return misperrors

    time.sleep(1)
    r, status_ok = expand_subdomains(api, domain)

    if status_ok:
        if r:
            result_filtered['results'].extend(r)
    else:
        misperrors['error'] = misperrors['error'] + ' Error subdomains result'
        return misperrors

    time.sleep(1)
    r, status_ok = expand_whois(api, domain)

    if status_ok:
        if r:
            result_filtered['results'].extend(r)
    else:
        misperrors['error'] = misperrors['error'] + ' Error whois result'
        return misperrors

    time.sleep(1)
    r, status_ok = expand_history_ipv4_ipv6(api, domain)
    #

    if status_ok:
        if r:
            result_filtered['results'].extend(r)
    else:
        misperrors['error'] = misperrors['error'] + ' Error history ipv4'
        return misperrors

    time.sleep(1)

    r, status_ok = expand_history_dns(api, domain)

    if status_ok:
        if r:
            result_filtered['results'].extend(r)
    else:
        misperrors['error'] = misperrors[
                                  'error'] + ' Error in expand History DNS'
        return misperrors
    print(result_filtered)
    print(misperrors)
    return result_filtered


def handle_ip(api, ip, misperrors):
    pass


def expand_domain_info(api, misperror, domain):
    r = []
    status_ok = False
    ns_servers = []
    list_ipv4 = []
    list_ipv6 = []
    servers_mx = []
    soa_hostnames = []

    results = api.domain(domain)

    if results:
        status_ok = True
        if 'current_dns' in results:
            if 'values' in results['current_dns']['ns']:
                ns_servers = [ns_entry['nameserver'] for ns_entry in
                              results['current_dns']['ns']['values']
                              if 'nameserver' in ns_entry]
            if 'values' in results['current_dns']['a']:
                list_ipv4 = [a_entry['ip'] for a_entry in
                             results['current_dns']['a']['values'] if
                             'ip' in a_entry]

            if 'values' in results['current_dns']['aaaa']:
                list_ipv6 = [ipv6_entry['ipv6'] for ipv6_entry in
                             results['current_dns']['aaaa']['values'] if
                             'ipv6' in ipv6_entry]

            if 'values' in results['current_dns']['mx']:
                servers_mx = [mx_entry['hostname'] for mx_entry in
                              results['current_dns']['mx']['values'] if
                              'hostname' in mx_entry]
            if 'values' in results['current_dns']['soa']:
                soa_hostnames = [soa_entry['email'] for soa_entry in
                                 results['current_dns']['soa']['values'] if
                                 'email' in soa_entry]

        if ns_servers:
            r.append({'types': ['domain'],
                      'values': ns_servers,
                      'categories': ['Network activity'],
                      'comment': 'List of name servers  of %s first seen %s ' %
                                 (domain,
                                  results['current_dns']['ns']['first_seen'])
                      })

        if list_ipv4:
            r.append({'types': ['domain|ip'],
                      'values': ['%s|%s' % (domain, ipv4) for ipv4 in
                                 list_ipv4],
                      'categories': ['Network activity'],

                      'comment': ' List ipv4 of %s first seen %s' %
                                 (domain,
                                  results['current_dns']['a']['first_seen'])

                      })
        if list_ipv6:
            r.append({'types': ['domain|ip'],
                      'values': ['%s|%s' % (domain, ipv6) for ipv6 in
                                 list_ipv6],
                      'categories': ['Network activity'],
                      'comment': ' List ipv6 of %s first seen %s' %
                                 (domain,
                                  results['current_dns']['aaaa']['first_seen'])

                      })

        if servers_mx:
            r.append({'types': ['domain'],
                      'values': servers_mx,
                      'categories': ['Network activity'],
                      'comment': ' List mx of %s first seen %s' %
                                 (domain,
                                  results['current_dns']['mx']['first_seen'])

                      })
        if soa_hostnames:
            r.append({'types': ['domain'],
                      'values': soa_hostnames,
                      'categories': ['Network activity'],
                      'comment': ' List soa of %s first seen %s' %
                                 (domain,
                                  results['current_dns']['soa']['first_seen'])
                      })

    return r, status_ok


def expand_subdomains(api, domain):
    r = []
    status_ok = False

    try:
        results = api.subdomains(domain)

        if results:
            status_ok = True
            if 'subdomains' in results:
                r.append({
                    'types': ['domain'],
                    'values': ['%s.%s' % (sub, domain)
                               for sub in results['subdomains']],
                    'categories': ['Network activity'],
                    'comment': 'subdomains of %s' % domain
                }

                )
    except APIError as e:
        misperrors['error'] = e

    return r, status_ok


def expand_whois(api, domain):
    r = []
    status_ok = False

    try:
        results = api.whois(domain)

        if results:
            status_ok = True
            item_registrant = __select_registrant_item(results)
            if item_registrant:

                if 'email' in item_registrant:
                    r.append(
                        {
                            'types': ['whois-registrant-email'],
                            'values': [item_registrant['email']],
                            'categories': ['Attribution'],
                            'comment': 'Whois information of %s by securitytrails'
                                       % domain
                        }
                    )

                if 'telephone' in item_registrant:
                    r.append(
                        {
                            'types': ['whois-registrant-phone'],
                            'values': [item_registrant['telephone']],
                            'categories': ['Attribution'],
                            'comment': 'Whois information of %s by securitytrails'
                                       % domain
                        }
                    )

                if 'name' in item_registrant:
                    r.append(
                        {
                            'types': ['whois-registrant-name'],
                            'values': [item_registrant['name']],
                            'categories': ['Attribution'],
                            'comment': 'Whois information of %s by securitytrails'
                                       % domain
                        }
                    )

                if 'registrarName' in item_registrant:
                    r.append(
                        {
                            'types': ['whois-registrar'],
                            'values': [item_registrant['registrarName']],
                            'categories': ['Attribution'],
                            'comment': 'Whois information of %s by securitytrails'
                                       % domain
                        }
                    )

                if 'createdDate' in item_registrant:
                    r.append(
                        {
                            'types': ['whois-creation-date'],
                            'values': [item_registrant['createdDate']],
                            'categories': ['Attribution'],
                            'comment': 'Whois information of %s by securitytrails'
                                       % domain
                        }
                    )

    except APIError as e:
        misperrors['error'] = e
        print(e)

    return r, status_ok


def expand_history_ipv4_ipv6(api, domain):
    r = []
    status_ok = False

    try:
        results = api.history_dns_ipv4(domain)

        if results:
            status_ok = True
            r.extend(__history_ip(results, domain))

        time.sleep(1)
        results = api.history_dns_aaaa(domain)

        if results:
            status_ok = True
            r.extend(__history_ip(results, domain, type_ip='ipv6'))

    except APIError as e:
        misperrors['error'] = e
        return [], False

    return r, status_ok


def expand_history_dns(api, domain):
    r = []
    status_ok = False

    try:

        results = api.history_dns_ns(domain)
        if results:
            r.extend(__history_dns(results, domain, 'nameserver', 'ns'))

        time.sleep(1)

        results = api.history_dns_soa(domain)

        if results:
            r.extend(__history_dns(results, domain, 'email', 'soa'))

        time.sleep(1)

        results = api.history_dns_mx(domain)

        if results:
            status_ok = True
            r.extend(__history_dns(results, domain, 'host', 'mx'))

    except APIError as e:
        misperrors['error'] = e
        return [], False

    status_ok = True

    return r, status_ok


def expand_history_whois(api, domain):
    r = []
    status_ok = False
    try:
        results = api.history_whois(domain)

        if results:

            if 'items' in results['results']:
                for item in results['results']['items']:
                    item_registrant = __select_registrant_item(item)

                    r.extend(
                        {
                            'type': ['domain'],
                            'values': item['nameServers'],
                            'categories': ['Network activity'],
                            'comment': 'Whois history Name Servers of %s '
                                       'Status: %s ' % (domain, item['status'])

                        }
                    )
                    if 'email' in item_registrant:
                        r.append(
                            {
                                'types': ['whois-registrant-email'],
                                'values': [item_registrant['email']],
                                'categories': ['Attribution'],
                                'comment': 'Whois history registrant email of %s'
                                           'Status: %s' % (
                                               domain, item['status'])
                            }
                        )

                    if 'telephone' in item_registrant:
                        r.append(
                            {
                                'types': ['whois-registrant-phone'],
                                'values': [item_registrant['telephone']],
                                'categories': ['Attribution'],
                                'comment': 'Whois history registrant phone of %s'
                                           'Status: %s' % (
                                               domain, item['status'])
                            }
                        )




    except APIError as e:
        misperrors['error'] = e
        return [], False



    return r, status_ok


def __history_ip(results, domain, type_ip='ip'):
    r = []
    if 'records' in results:
        for record in results['records']:
            if 'values' in record:
                for item in record['values']:
                    r.append(
                        {'types': ['domain|ip'],
                         'values': ['%s|%s' % (domain, item[type_ip])],
                         'categories': ['Network activity'],
                         'comment': 'History IP on securitytrails %s '
                                    'last seen: %s first seen: %s' %
                                    (domain, record['last_seen'],
                                     record['first_seen'])
                         }
                    )

    return r


def __history_dns(results, domain, type_serv, service):
    r = []

    if 'records' in results:
        for record in results['records']:
            if 'values' in record:
                values = record['values']
                if type(values) is list:

                    for item in record['values']:
                        r.append(
                            {'types': ['domain|ip'],
                             'values': [item[type_serv]],
                             'categories': ['Network activity'],
                             'comment': 'history %s of %s last seen: %s first seen: %s' %
                                        (service, domain, record['last_seen'],
                                         record['first_seen'])
                             }
                        )
                else:
                    r.append(
                        {'types': ['domain|ip'],
                         'values': [values[type_serv]],
                         'categories': ['Network activity'],
                         'comment': 'history %s of %s last seen: %s first seen: %s' %
                                    (service, domain, record['last_seen'],
                                     record['first_seen'])
                         }
                    )
    return r

def introspection():
    return mispattributes


def version():
    moduleinfo['config'] = moduleconfig
    return moduleinfo


def __select_registrant_item(entry):
    if 'contacts' in entry:
        for c in entry['contacts']:

            if c['type'] == 'registrant':
                return c
