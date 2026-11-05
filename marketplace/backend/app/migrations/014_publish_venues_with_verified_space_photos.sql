-- Publish the catalog venues whose photo shows the venue's own meeting or event space, taken from its own
-- website. Their names, addresses, and room counts were checked against those sites when the photos were found.
-- Venues with only a facade, lobby, or listing photo stay unpublished, as do Spaces Powerhouse (unclear operator),
-- BargaFlyt (no working website), and Quality Hotel Augustin (opens in 2027).
-- Equipment and prices are still placeholders until each venue confirms them.
-- Only seeded rows carrying the verified photo are published; host-owned rooms are left alone.
UPDATE marketplace_rooms
SET published = true
WHERE owner_id IS NULL AND image_key = venue || '-venue' AND venue IN (
    'scandic-bakklandet', 'scandic-hell', 'scandic-lerkendal', 'scandic-nidelven', 'scandic-solsiden',
    'radisson-royal-garden', 'radisson-airport',
    'rockheim', 'salemhuset', 'trondheim-spektrum', 'banksalen', 'olavshallen', 'lager11', 'olo'
);
