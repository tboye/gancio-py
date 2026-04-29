from enum import Enum


class TextSetting(str, Enum):
    TITLE = 'title'
    DESCRIPTION = 'description'
    ABOUT = 'about'
    BASEURL = 'baseurl'
    ADMIN_EMAIL = 'admin_email'
    INSTANCE_TIMEZONE = 'instance_timezone'
    INSTANCE_LOCALE = 'instance_locale'
    INSTANCE_NAME = 'instance_name'
    CUSTOM_JS = 'custom_js'
    CUSTOM_CSS = 'custom_css'
    GEOCODING_PROVIDER = 'geocoding_provider'
    GEOCODING_PROVIDER_TYPE = 'geocoding_provider_type'
    TILELAYER_PROVIDER = 'tilelayer_provider'
    TILELAYER_PROVIDER_ATTRIBUTION = 'tilelayer_provider_attribution'


class BoolSetting(str, Enum):
    ALLOW_REGISTRATION = 'allow_registration'
    ALLOW_ANON_EVENT = 'allow_anon_event'
    ALLOW_MULTIDATE_EVENT = 'allow_multidate_event'
    ALLOW_RECURRENT_EVENT = 'allow_recurrent_event'
    ALLOW_EVENT_WITHOUT_END_TIME = 'allow_event_without_end_time'
    ALLOW_ONLINE_EVENT = 'allow_online_event'
    ALLOW_GEOLOCATION = 'allow_geolocation'
    SHOW_DOWNLOAD_MEDIA = 'show_download_media'
    ENABLE_MODERATION = 'enable_moderation'
    ENABLE_REPORT = 'enable_report'
    ENABLE_FEDERATION = 'enable_federation'
    ENABLE_RESOURCES = 'enable_resources'
    FEDERATED_EVENTS_IN_HOME = 'federated_events_in_home'
    RECURRENT_EVENT_VISIBLE = 'recurrent_event_visible'
    HIDE_BOOSTS = 'hide_boosts'
    HIDE_THUMBS = 'hide_thumbs'
    HIDE_CALENDAR = 'hide_calendar'
    THEME_IS_DARK = 'theme.is_dark'


class JsonSetting(str, Enum):
    GEOCODING_COUNTRYCODES = 'geocoding_countrycodes'
    DEFAULT_FEDI_HASHTAGS = 'default_fedi_hashtags'
    FOOTER_LINKS = 'footerLinks'
    DARK_COLORS = 'dark_colors'
    LIGHT_COLORS = 'light_colors'
    PLUGINS = 'plugins'
    SMTP = 'smtp'
    COLLECTION_IN_HOME = 'collection_in_home'
    CALENDAR_FIRST_DAY_OF_WEEK = 'calendar_first_day_of_week'
