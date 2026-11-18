[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=PopinjayJohn&repository=daily-animalcrackers&category=integration)

# Daily Animal Crackers for Home Assistant
Gets the daily Animal Crackers comic from [comiccaster](https://comiccaster.xyz/rss/animalcrackers) (`https://comiccaster.xyz/rss/animalcrackers`) and displays it as an image entity in Home Assistant.

Forked from [Aasikki/daily-fingerpori](https://github.com/Aasikki/daily-fingerpori).

Best when used together with a comic card such as https://github.com/Aasikki/comic-card, but of course you can use any card that can display images from image entities, like the built-in picture card.

## Installation and configuration:

 1. The integration can be installed from [HACS](https://hacs.xyz/). Instructions for using HACS can be found [here](https://hacs.xyz/docs/use/).

 2. After installing, set up the integration in Home Assistant from: <br> `Settings -> Devices & services -> Add integration -> Daily Animal Crackers`.

 3. From here you can change the comic update interval (default recommendation: 3 hours), <br> and press "Submit", after which the integration is in use!

## Usage:
After setting up the integration, you should find an integration called `Daily Animal Crackers` from the `Devices & services` -page, where you can find the comic as a picture entity, as well as a button for manually updating the comic.

> **Tip!**
> If you want to update the comic at a specific time, you can make an automation that will update the comic using the update button (the comic will still also be updated by the configured update interval).
