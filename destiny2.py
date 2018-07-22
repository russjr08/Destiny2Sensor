import pydest
import asyncio

import voluptuous as vol

from homeassistant.helpers.entity import Entity

from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_NAME, CONF_API_KEY

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_API_KEY): cv.string
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices):
    player_name = config.get(CONF_NAME)
    api_key = config.get(CONF_API_KEY)

    async_add_devices(Destiny2Sensor(player_name, api_key), True)


class Destiny2Sensor(Entity):

    def __init__(self, player_name, api_key):
        self._state = "Updating"
        self._name = player_name
        self._api_key = api_key

        self.place = "Unknown"
        self.latest_character_played_date = "0000-00-00T00:00:00Z"
        self.membership_id = "Unknown"
        self.membership_type = 0
        self.current_character_id = "Unknown"
        self.current_activity_type = 0
        self.current_activity_started = "0000-00-00T00:00:00Z"

    @property
    def state(self):
        """Returns logged in character's game state (such as 'In Orbit')"""
        return self._state

    @property
    def name(self):
        return self._name

    @property
    def state_attributes(self):
        return [self.place, self.latest_character_played_date, self.membership_id, self.membership_type,
                self.current_character_id, self.current_activity_type, self.current_activity_started]

    async def update(self):
        destiny = pydest.Pydest(self._api_key)

        await destiny.update_manifest()

        """Searches for the given player name, and grabs their platform and ID"""
        search = await destiny.api.search_destiny_player(-1, self._name)
        data = search['Response'][0]
        self.membership_id = data['membershipId']
        self.membership_type = data['membershipType']
        self._name = data['displayName']
        profile = await destiny.api.get_profile(data['membershipType'], data['membershipId'], [200])

        """Finds all characters, and checks to see which character was last logged in"""
        character_dates = []

        for i, (key, value) in enumerate(profile['Response']['characters']['data'].items()):
            print(key, value)
            character_dates.append(value['dateLastPlayed'])

        latest_character_played_date = max(character_dates)

        latest_character = None

        for i, (key, value) in enumerate(profile['Response']['characters']['data'].items()):
            if value['dateLastPlayed'] == latest_character_played_date:
                latest_character = value
                self.latest_character_played_date = latest_character_played_date
                self.current_character_id = value['characterId']

        latest_character = await destiny.api.get_character(data['membershipType'], data['membershipId'],
                                                           latest_character['characterId'], [204])

        """Attempts to find attributes about current activity/place"""

        if 'currentActivityHash' in latest_character['Response']['activities']['data']:
            current_activity = await destiny.decode_hash(
                latest_character['Response']['activities']['data']['currentActivityHash'], "DestinyActivityDefinition")
            self.current_activity_started = latest_character['Response']['activities']['data']['dateActivityStarted']

            try:
                current_activity_mode = await destiny.decode_hash(
                    latest_character['Response']['activities']['data']['currentActivityModeHash'],
                    "DestinyActivityModeDefinition")
            except pydest.PydestException:
                current_activity_mode = 'Unknown'
        if 'currentActivityModeType' in latest_character['Response']['activities']['data']:
            self.current_activity_type = latest_character['Response']['activities']['data']['currentActivityModeType']
        else:
            self.current_activity_type = 0

        self.place = await destiny.decode_hash(current_activity["placeHash"], "DestinyPlaceDefinition")['displayProperties']['name']
        self._state = await destiny.decode_hash(current_activity["placeHash"], "DestinyPlaceDefinition")['displayProperties']['description']
        destiny.close()


# TESTING

async def main():
    """You will need to add your api key!"""
    destiny = pydest.Pydest('KEY_GOES_HERE')

    """Insert your gamertag/PSN ID/Battle Net name here"""
    player_name = "CivilExponent"
    await destiny.update_manifest()

    """Searches for the given player name, and grabs their platform and ID"""
    search = await destiny.api.search_destiny_player(-1, player_name)
    data = search['Response'][0]
    profile = await destiny.api.get_profile(data['membershipType'], data['membershipId'], [200])

    """Finds all characters, and checks to see which character was last logged in"""
    character_dates = []

    for i, (key, value) in enumerate(profile['Response']['characters']['data'].items()):
        print(key, value)
        character_dates.append(value['dateLastPlayed'])

    latest_character_played_date = max(character_dates)

    latest_character = None

    for i, (key, value) in enumerate(profile['Response']['characters']['data'].items()):
        if value['dateLastPlayed'] == latest_character_played_date:
            latest_character = value

    latest_character = await destiny.api.get_character(data['membershipType'], data['membershipId'], latest_character['characterId'], [204])

    """Attempts to find attributes about current activity/place"""

    if 'currentActivityHash' in latest_character['Response']['activities']['data']:
        current_activity = await destiny.decode_hash(latest_character['Response']['activities']['data']['currentActivityHash'], "DestinyActivityDefinition")
        current_activity_started = latest_character['Response']['activities']['data']['dateActivityStarted']

        try:
            current_activity_mode = await destiny.decode_hash(latest_character['Response']['activities']['data']['currentActivityModeHash'], "DestinyActivityModeDefinition")
        except pydest.PydestException:
            current_activity_mode = 'Unknown'
    if 'currentActivityModeType' in latest_character['Response']['activities']['data']:
        current_activity_mode_type = latest_character['Response']['activities']['data']['currentActivityModeType']
    else:
        current_activity_mode_type = 0

    place = await destiny.decode_hash(current_activity["placeHash"], "DestinyPlaceDefinition")
    destiny.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()