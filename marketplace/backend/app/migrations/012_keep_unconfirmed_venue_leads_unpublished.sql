-- Keep the 011 prospect research as drafts until the venues and rates are confirmed.
-- Existing booking records and rooms published by their hosts are preserved.
UPDATE marketplace_rooms
SET published = false
WHERE owner_id IS NULL AND published AND id IN (
    'workwork-meeting-room', 'bargaflyt-small-room',
    'bargaflyt-large-room', 'olo-workshop',
    'spaces-powerhouse-meeting-room', 'spaces-powerhouse-boardroom',
    'clarion-trondheim-meeting-room', 'clarion-trondheim-boardroom',
    'radisson-royal-garden-meeting-room', 'radisson-royal-garden-boardroom',
    'radisson-airport-meeting-room', 'scandic-lerkendal-meeting-room',
    'scandic-lerkendal-boardroom', 'scandic-nidelven-meeting-room',
    'scandic-nidelven-conference-room', 'scandic-solsiden-meeting-room',
    'scandic-solsiden-conference-room', 'scandic-bakklandet-meeting-room',
    'scandic-hell-meeting-room', 'scandic-hell-boardroom',
    'britannia-boardroom', 'britannia-meeting-room',
    'quality-prinsen-meeting-room', 'quality-panorama-meeting-room',
    'quality-panorama-boardroom', 'quality-augustin-meeting-room',
    'comfort-park-meeting-room', 'comfort-trondheim-meeting-room',
    'home-grand-olav-meeting-room', 'thon-nidaros-meeting-room',
    'olavshallen-meeting-room', 'olavshallen-small-hall',
    'trondheim-spektrum-meeting-room', 'trondheim-spektrum-boardroom',
    'rockheim-event-space', 'lager11-blackbox',
    'lager11-mathallen', 'salemhuset-meeting-room',
    'salemhuset-lillesal', 'salemhuset-storsal',
    'banksalen-hall'
);
