ALLOWED_CITIES = [
    'alappuzha', 'alleppey', 'cherthala', 'thuravoor',
    'arookutty', 'arthingal', 'chandiroor', 'eramalloor',
    'ezhupunna', 'kadakkarapally', 'kalavamkodam',
    'kanichukulangara', 'kannankara', 'karikad',
    'kochuramapuram', 'kokkothamangalam', 'kuthiathode',
    'manappuram', 'mararikulam', 'maruthorvattom',
    'mayithara', 'muhamma', 'muttathiparambu',
    'naduvathnagar', 'olavaipu', 'pallippuram',
    'pallithode', 'panavally', 'parayakad', 'pattanacaud',
    'perumbalam', 'poochackal', 'sethulekshmipuram',
    'thanneermukkom', 'thirumalabhagom', 'thirunallur',
    'thuravoor south', 'thycattussery', 'trichattukulam',
    'vaduthala', 'valamangalam', 'varanadu', 'varanam',
    'vayalar', 'vettackal',
]

def is_delivery_allowed(city):
    city_lower = str(city).strip().lower()
    return any(c in city_lower for c in ALLOWED_CITIES)