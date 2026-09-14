/**
 * Sample server catalog. This is the easiest file for teammates to edit.
 * id: unique URL-safe identifier (also used as an icon color class).
 * name, os, description: searchable/displayed server information.
 * protocol: reserved for the later backend integration; not displayed yet.
 * icon: trusted, developer-authored SVG markup only. Never insert API/user SVG.
 * These are examples, not reachable servers. Do not put credentials here.
 */
const DEMO_SERVERS = [
  {
    "id": "windows",
    "name": "Windows Server",
    "os": "Windows",
    "description": "Your Windows workspace",
    "protocol": "RDP",
    "icon": "<path d=\"M3 5 10 4v7H3zm9-1 9-1v8h-9zM3 13h7v7l-7-1zm9 0h9v8l-9-1z\" fill=\"currentColor\" stroke=\"none\"/>"
  },
  {
    "id": "linux",
    "name": "Linux Server",
    "os": "Linux",
    "description": "Your Linux environment",
    "protocol": "Remote desktop",
    "icon": "<path d=\"m5 7 5 5-5 5m8 0h6\"/>"
  },
  {
    "id": "ubuntu",
    "name": "Ubuntu Server",
    "os": "Ubuntu",
    "description": "Your Ubuntu workspace",
    "protocol": "Remote desktop",
    "icon": "<circle cx=\"12\" cy=\"12\" r=\"6\"/><circle cx=\"12\" cy=\"3\" r=\"2\" fill=\"currentColor\"/><circle cx=\"4\" cy=\"16\" r=\"2\" fill=\"currentColor\"/><circle cx=\"20\" cy=\"16\" r=\"2\" fill=\"currentColor\"/>"
  }
];
