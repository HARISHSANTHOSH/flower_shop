# Cherthala Taluk — all 51 post office pincodes (India Post verified)
ALLOWED_PINCODES = {
    '688523',  # Mararikulam North, Sethulekshmipuram
    '688524',  # Cherthala, Cherthala Cutcherry, Kalavamkodam
    '688525',  # Muhamma
    '688526',  # Manappuram, Naduvathnagar, Olavaipu, Panavally, Poochackal, Trichattukulam
    '688527',  # Kannankara, Karikad, Kokkothamangalam, Muttathiparambu, Thanneermukkom
    '688528',  # Thycattussery
    '688529',  # Kadakkarapally
    '688530',  # Arthingal, Chethy, Thaickal
    '688531',  # Andhakaranazhy, Pattanacaud
    '688532',  # Thuravoor, Thuravoor South, Valamangalam
    '688533',  # Kuthiathode
    '688535',  # Arookutty, Vaduthala Jetty
    '688537',  # Chandiroor, Eramallur, Ezhupunna, Ezhupunna South
    '688539',  # Cherthala South, Kuruppankulangara, Maruthorvattom, Mayithara, Varanadu
    '688540',  # Pallithode, Parayakad, Thirumalabhagom
    '688541',  # Kochuramapuram, Pallippuram, Thirunallur
    '688555',  # Varanam
    '688557',  # Vayalar
    '688570',  # Perumbalam
    '688582',  # Kanichukulangara, Sreenarayanapuram
}


def is_delivery_allowed(pincode: str) -> bool:
    """Return True if the pincode is within Cherthala Taluk delivery zone."""
    return str(pincode).strip() in ALLOWED_PINCODES