# Furizon Webint
Furizon Webint is a powerful control panel designed to complement Pretix, providing management of various aspects related to the attendance of participants at furry conventions. Originally developed for Furizon Beyond (2023), this application is currently undergoing a rehaul to become more versatile and adaptable for use in any convention.

## How does it work?
The integration with Pretix is achieved by leveraging a simple nginx rule. When individuals place orders through Pretix, they usually receive a "magic" link that allows them to manage their order. Using a nginx rule, we redirect these requests to this backend. This process is seamless because the essential information needed for managing Pretix orders can still be accessed via a shorter URL without compromising any functionality.

## Why not a pretix plugin?
Developing plugins for Pretix was far too tedious, and Pretix didn't have the flexibility needed for this panel.

## What can it do?
- User badges management (allow attendees to upload pictures within the deadlines)
- Manage hotel rooms (attendees can create, join, delete rooms)
- Show a nosecount public page
- Data export
- Car pooling (let attendees post announcements and organize trips)
- Karaoke Queue management (apply to sing for the karaoke contest and manage the queue)
- Manage the events and present them via API for usage with he app
- Export an API to be used for the mobile app (no plans to open source that, sorry ☹️)
- Check-in management

## How to run it
1.  Create a Python virtual environment (venv).
2.  Install the required dependencies from the `requirements.txt` file.
3.  Edit the `config.py` file with your specific data. You can use `config.example.py` as a template to guide you.
4.  Set up an nginx rule to redirect requests for `/manage/` and `/[a-z0-9]+/[a-z0-9]+/order/[A-Z0-9]+/[a-z0-9]+/open/[a-z0-9]+/` to the Furizon Webint backend.
5.  Run `app.py`. By default, the application will listen on `0.0.0.0:8188`.
