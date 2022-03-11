import imp
from typing import Tuple
from nautobot.extras.plugins import PluginTemplateExtension
from nautobot.circuits.models import Circuit, CircuitTermination
from nautobot.dcim.models import Site, Interface

SITE_OBJECT_KEY = 'site'
SITE_ENDPOINTS_KEY = 'devices'
SITE_CONNECTIONS_KEY = 'connections'
LOCAL_DEVICE_KEY = 'local_device'
REMOTE_DEVICE_KEY = 'remote_device'
CONNECTION_COUNT_KEY = 'connection_count'
CIRCUIT_KEY = 'circuit'


def get_connected_sites(site: Site) -> Tuple[list, dict]:
    """ Fetch a list of sites connected to the given site by a circuit and the local devices connected to those circuits """

    sites = {}
    local_devices = {}
    terminations = CircuitTermination.objects.filter(circuit__terminations__site=site.id).prefetch_related('site', '_path__destination')
    #terminations = CircuitTermination.objects.filter(circuit__terminations__site=site.id).prefetch_related('site')
    for termination in terminations:
        connected_interface = termination.connected_endpoint
        connected_site = termination.site
        connected_device = connected_interface.device if connected_interface else None
        if connected_site.slug == site.slug:
            local_devices[termination.circuit.pk] = connected_device
            continue
        # Got a circuit termination on another site that is connected to this site by a circuit
        new_endpoint = { REMOTE_DEVICE_KEY: connected_device, CIRCUIT_KEY: termination.circuit.pk }
        if connected_site.slug in sites:
            site_info = sites[connected_site.slug]
            site_info[SITE_ENDPOINTS_KEY].append(new_endpoint)
        else:
            sites[connected_site.slug] = { 
                SITE_OBJECT_KEY: connected_site,
                SITE_ENDPOINTS_KEY: [new_endpoint],
            }
    
    return (list(sites.values()), local_devices)


class SiteContent(PluginTemplateExtension): # pylint: disable=abstract-method
    """Show information about circuits to other sites on Site objects."""

    model = "dcim.site"

    def right_page(self):
        site = self.context["object"]
        (sites, local_devices) = get_connected_sites(site)

        # Don't show the panel if there are no connected sites 
        if not sites:
          return ""

        # Combine the data into one list of remote sites with per site the connected devices and the amount of connections
        for site_info in sites:
            device_pair_connections = {}
            # Condense the individual connections list for this site to a list per device pair
            if len(site_info[SITE_ENDPOINTS_KEY]) == 0:
                device_pair_connections['--:--'] = { 
                    LOCAL_DEVICE_KEY: None,
                    REMOTE_DEVICE_KEY: None,
                    CONNECTION_COUNT_KEY: None
                }
            else:
                for endpoint_info in site_info[SITE_ENDPOINTS_KEY]:
                    local_device = local_devices.get(endpoint_info[CIRCUIT_KEY])
                    local_device_name = local_device.name if local_device else '--'
                    remote_device = endpoint_info[REMOTE_DEVICE_KEY]
                    remote_device_name = remote_device.name if remote_device else '--'
                    device_pair_name =  f"{local_device_name}:{remote_device_name}"
                    if device_pair_name in device_pair_connections:
                        device_pair_info = device_pair_connections[device_pair_name]
                        device_pair_info[CONNECTION_COUNT_KEY] += 1
                    else:
                        device_pair_connections[device_pair_name] = { 
                            LOCAL_DEVICE_KEY: local_device,
                            REMOTE_DEVICE_KEY: remote_device,
                            CONNECTION_COUNT_KEY: 1
                        }
            # Add connection list to site_info
            site_info[SITE_CONNECTIONS_KEY] = list(device_pair_connections.values())
            # Remove information no longer neccesary from site_info
            site_info.pop(SITE_ENDPOINTS_KEY)

        # At this point sites is a dict with the slug of all connected sites as key and values:
        # {
        #   SITE_OBJECT_KEY: <site object of connected site>
        #   SITE_CONNECTIONS_KEY: [ {
        #     LOCAL_DEVICE_KEY: <local device object>
        #     REMOTE_DEVICE_KEY: <remote device object>
        #     CONNECTION_COUNT_KEY: <connection count>
        #   } ]
        # }
        #

        return self.render(
            "nautobot_show_connections/site-connections.html",
            extra_context={
                "connected_sites": sites,
            },
        )


class DeviceContent(PluginTemplateExtension): # pylint: disable=abstract-method
    """Show information about circuits to other sites on Device objects."""

    model = "dcim.device"

    def right_page(self):
        device = self.context["object"]

        terminations = CircuitTermination.objects.filter(site=device.site.id, _path__isnull=False).prefetch_related('circuit', '_path__destination')
        #terminations = CircuitTermination.objects.filter(site=device.site.id, _path__isnull=False).prefetch_related('circuit')
        connections = []
        for termination in terminations:
            interface = termination.connected_endpoint
            if interface and interface.device.pk == device.pk:
                remote_interface = interface.connected_endpoint
                connections.append({
                        'circuit': termination.circuit,
                        'local_interface': interface,
                        'remote_device': remote_interface.device,
                        'remote_interface': remote_interface
                    })

        # Don't show the panel if there are no connections 
        if not connections:
          return ""

        return self.render(
            "nautobot_show_connections/device-connections.html",
            extra_context={
                "connected_circuits": connections,
            },
        )


template_extensions = [SiteContent, DeviceContent]
