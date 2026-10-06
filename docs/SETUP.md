# Complete setup guide

## 1. Decide which laptop does what

This guide assumes x86-64/Intel/AMD laptops and a current OS supported by your
chosen Docker and hypervisor releases. Apple Silicon/ARM and unsupported old
Windows hosts need a different virtualization plan.

- **Laptop 1** runs this Docker Compose stack (the website and gateway).
- **Laptop 2** runs a Windows VM in VirtualBox initially.
- Both connect to the same private network. Ethernet is preferable when available.
- The VM runs its own OS and remote desktop service. No containers or Python code
  need to be installed inside the Windows VM.
- Later, add more VMs on either laptop. Use one shared AnyAccess gateway initially.

Do not erase either laptop or change its host OS for this setup. Back up important
files before installing a hypervisor. Keep enough RAM for the host plus Docker or
VMs. Start with one VM and measure usage rather than allocating all host RAM.

## 2. Install tools on Laptop 1

Install Python 3 (used by the setup script) and Docker with Compose v2.
On supported Windows hosts, install Docker Desktop with its Linux-container /
WSL 2 backend, following https://docs.docker.com/desktop/setup/install/windows-install/.
On Linux, use the distribution-specific official Docker Engine instructions and
install the Compose plugin. Docker Desktop is not required on Linux.

Open a terminal and confirm:

```bash
python --version
docker version
docker compose version
```

On Windows, `py` may replace `python`. On Linux/macOS, use `python3` if needed.
Docker Desktop must be running. Docker and VirtualBox on the same Windows host
can compete for virtualization resources; the initial two-laptop split avoids
making that combination a requirement.

## 3. Create a Windows VM on Laptop 2

1. Install VirtualBox from its official website and obtain a legitimate Windows
   installation image and license appropriate for your use.
2. Create the VM and install a supported **Windows Pro/Enterprise/Education or
   Windows Server edition that supports hosting RDP**. Windows Home can be a
   client but cannot host Microsoft's built-in RDP service.
3. Allocate resources within your laptop's capacity and the guest OS requirements.
   Do not install an unsupported Windows version just to save RAM.
4. In the powered-off VM's **Settings → Network → Adapter 1**, choose
   **Bridged Adapter**, selecting the physical Ethernet/Wi-Fi adapter in use.
5. Boot the VM. Inside Windows, open a terminal and run:

   ```powershell
   ipconfig
   ```

6. Record the VM's IPv4 address. Example only: `192.168.1.101`.
7. Inside the VM, open **Settings → System → Remote Desktop** and enable it.
   Keep Network Level Authentication enabled.
8. Use a Windows account with a real password. A Windows Hello PIN is not the
   account password used for RDP. A dedicated local non-admin account is simpler
   for a lab; add it to the permitted Remote Desktop users.
9. Check the Windows firewall's Remote Desktop rule. Restrict inbound access to
   the gateway laptop/network appropriate for your lab; do not disable the firewall.
10. Keep the guest and host awake while testing. Closing the laptop lid may put
    the host to sleep and make every hosted VM unreachable.

When possible, reserve the VM's address in your router's DHCP configuration so
it does not change after reboot. Ordinary desktop Windows sessions are not a
multi-user server: another login can lock/displace the console or another user.
Use separate VMs for separate concurrent desktops in this first version.

### If bridged networking does not work

Some Wi-Fi adapters, guest networks, and access points prevent bridging or
client-to-client traffic. Move to Ethernet or a non-isolated private network.
Alternatively, configure VirtualBox **NAT → Advanced → Port Forwarding**:

| Field | Example |
| --- | --- |
| Name | windows-rdp |
| Protocol | TCP |
| Host IP | Laptop 2's LAN IPv4 address, e.g. 192.168.1.30 |
| Host port | 13389 |
| Guest IP | Leave blank for the default DHCP guest, or specify its NAT IP |
| Guest port | 3389 |

Allow that host port from Laptop 1 through Laptop 2's firewall. In AnyAccess,
use **Laptop 2's LAN IP and port 13389**, not the guest's NAT-only address.
This is VirtualBox host forwarding, not a router/internet port-forward rule.
Each additional NAT VM needs a different host port. Never enter `localhost` as
the VM hostname: within guacd that means the guacd container itself.

## 4. Start AnyAccess locally on Laptop 1

Extract the ZIP. Open a terminal inside `AnyAccess-backend`, where `compose.yaml`
and `manage.py` are located. Run:

```bash
python scripts/setup_env.py
docker compose up -d --build
docker compose ps
docker compose logs --tail=60 web guacamole guacd
```

The setup script creates three random keys in `.env` and refuses to overwrite an
existing file. Keep the keys: changing CREDENTIAL_KEY makes existing saved
passwords unreadable. The migrate container should finish with exit code 0;
that is expected. The other services remain running.

The first build downloads images and Python packages. Wait for the web service
to be healthy and Guacamole/Tomcat to finish starting. If port 8080 is occupied,
change both HTTP_PORT and the port in PUBLIC_ORIGIN in `.env`, then rerun Compose.

Default `.env` networking:

```dotenv
PUBLIC_ORIGIN=http://localhost:8080
BIND_ADDRESS=127.0.0.1
HTTP_PORT=8080
```

This intentionally binds the web entrypoint to Laptop 1's loopback interface for
the first test. The RDP connection still travels from guacd to the remote VM.
Use `localhost` consistently in the browser; mixing IPs and names creates
separate cookies and will fail the gateway's exact origin check.

## 5. Confirm the gateway network can reach the VM

A successful ping is not sufficient. Test the actual TCP port.
From Windows Laptop 1, one useful first test is:

```powershell
Test-NetConnection 192.168.1.101 -Port 3389
```

Replace the IP with YOUR VM address. Also test from the guacd container's network
namespace, which is the path that actually matters. These commands open and
close a TCP connection without attempting to log in.

**PowerShell:**

```powershell
$guacdId = docker compose ps -q guacd
docker run --rm --network "container:$guacdId" python:3.12-slim python -c "import socket; s=socket.create_connection(('192.168.1.101',3389),5); s.close(); print('RDP port reachable')"
```

**Bash:**

```bash
guacd_id=$(docker compose ps -q guacd)
docker run --rm --network "container:$guacd_id" python:3.12-slim python -c "import socket; s=socket.create_connection(('192.168.1.101',3389),5); s.close(); print('RDP port reachable')"
```

For NAT forwarding, replace both address and port. Fix networking/firewall issues
here before troubleshooting Django. Host-network reachability alone does not
prove container-network reachability.

## 6. Create the administrator and a normal user

```bash
docker compose exec web python manage.py createsuperuser
```

Choose your own username and password. No default administrator is included.
Open http://localhost:8080/admin/ and sign in.

1. Under Authentication and Authorization, add an ordinary User.
2. Keep that user's Active flag enabled.
3. Do not give ordinary users Staff or Superuser status.
4. Save the account with a strong password.

The administrator manages configuration. Normal users use the AnyAccess page.
Superusers can see all enabled servers; normal users see only assigned servers.

## 7. Register your Windows server

In the admin, open **Servers → Add**:

| Field | Example/value |
| --- | --- |
| Name | Windows Lab 01 |
| Operating system | Windows |
| Description | Windows VM on Laptop 2 |
| Protocol | RDP desktop |
| Hostname | Your VM IP, e.g. 192.168.1.101 |
| Port | 3389 (or your NAT host forwarding port) |
| Username | The VM's Windows account, e.g. labuser |
| Domain | Usually blank for a local account; use the correct domain if joined |
| Remote password | The account's actual password, not its PIN |
| RDP security | NLA for current Windows hosts |
| Ignore certificate | Leave off with a trusted certificate; for YOUR known lab VM's self-signed RDP certificate, enable it if certificate verification fails |
| Enabled | Checked |
| Allowed users | Move your ordinary user to the selected list |

Save. Passwords are encrypted before storage and are not displayed when editing.
Leaving Remote password blank preserves the saved password. Clear password is an
explicit separate checkbox. Never paste hostnames or credentials into JavaScript.

## 8. Test the full flow

1. Log out of admin.
2. Open http://localhost:8080/ and log in as the ordinary user.
3. Confirm only the assigned server appears.
4. Click Connect. You should see connection progress, then the Windows desktop.
5. Click inside the display, open Notepad, and type a short sentence.
6. Test mouse movement/clicks, resize, fullscreen, and Ctrl+Alt+Del.
7. Click Disconnect. The browser tunnel and gateway login are closed.
8. Log out and verify you cannot reopen the server page without logging in.

Disconnect ends remote access; it does not power off the VM or necessarily sign
out of Windows. Applications may remain running inside the Windows session.
The site does not manufacture an Online badge: a server being assigned does not
prove it is running.

## 9. Access AnyAccess from Laptop 2 over HTTPS

First finish the localhost test. For another device to open the website, enable
the included HTTPS profile rather than transmitting logins over LAN HTTP.

Assume Laptop 1's LAN IP is `192.168.1.20` (replace it everywhere below).
In `.env`, change:

```dotenv
PUBLIC_ORIGIN=https://192.168.1.20:8443
BIND_ADDRESS=0.0.0.0
HTTP_PORT=8080
```

Generate a certificate for that address. Run from the project folder after the
initial image build:

```bash
docker compose run --rm --no-deps --user root --volume ./deploy/certs:/certs web python scripts/create_tls.py --hostname 192.168.1.20
docker compose -f compose.yaml -f compose.https.yaml up -d --build
```

The certificate script uses cryptography inside the Docker image; no host pip
installation is needed. It refuses to overwrite a non-empty certificate folder.
The HTTPS profile redirects port 8080 to HTTPS port 8443.

Trust `deploy/certs/lab-ca.crt` on every browser device using the private lab:

- On Windows, open the certificate → Install Certificate → Current User →
  Place all certificates in the following store → Trusted Root Certification
  Authorities. Only trust the certificate you just generated for your own lab.
- Some browsers maintain their own certificate store; import the same public CA
  certificate there if the OS trust store is not used.
- Share only `lab-ca.crt`, NEVER `lab-ca.key` or `server.key`.

Allow inbound TCP 8443 to Laptop 1 on its private network. A Windows administrator
can add a scoped rule (adjust for your network policy):

```powershell
New-NetFirewallRule -DisplayName "AnyAccess HTTPS lab" -Direction Inbound -Protocol TCP -LocalPort 8443 -Action Allow -Profile Private -RemoteAddress LocalSubnet
```

Open **https://192.168.1.20:8443/** from both laptops. Do not keep using localhost
when PUBLIC_ORIGIN specifies the LAN IP. A matching, trusted certificate is
required for a clean browser experience. If the host IP changes, reserve it or
issue a certificate for the new address and update PUBLIC_ORIGIN.

For every later HTTPS start/build, include both Compose files. Example:

```bash
docker compose -f compose.yaml -f compose.https.yaml up -d --build
```

## 10. Add the other operating systems

The simplest Linux addition is a Linux desktop VM with its own working RDP or
VNC service. A bare server install may have no graphical desktop to display.
For example, an Ubuntu desktop running xrdp can be added as protocol RDP on 3389;
choose TLS for RDP security if its configuration does not use NLA. The OS label
is descriptive and does not install a remote desktop service.

For a terminal-only Linux server, enable SSH and register protocol SSH on port
22 with the correct username/password. The current admin supports password-based
SSH, not private-key provisioning. SSH will show a terminal, not a full desktop.
For VNC, configure an actual VNC server first and set its port (often 5900, but
use its actual configuration). This project does not install these services.

Repeat server registration for each target, wherever it is hosted. Start small;
VM concurrency is limited by each laptop's CPU, RAM, and storage, not by how many
cards you add to the website.

## 11. Access from outside your home

Do not forward RDP port 3389, guacd 4822, or the Guacamole container directly to
the internet. For a project lab, put both clients and the gateway laptop on a
private VPN, then serve the same HTTPS site over the reachable VPN address or DNS
name. Update PUBLIC_ORIGIN, its certificate, and firewall rules to match.

VPN installation and public hosting depend on your actual OS/router and are not
automated here. Public multi-user deployment also needs operational hardening,
MFA/rate-limit review, backups, and resource controls beyond this small lab build.

The old `chatgpt.site` preview remains a separate static preview. This package
serves the frontend and backend together on your laptop. Uploading these Python
files to that preview will not run Django or connect it to your LAN.
