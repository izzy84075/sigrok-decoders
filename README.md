A collection of Sigrok protocol decoders for various protocols I work with.

==ir_ltto==

A basic decoder that pulls out LTTO/LTX/LTAR laser tag IR signatures. Gives sync length, number of bits, and the data.

==ir_ltto_decode==

Takes the output from ir_ltto and gets the details of the data out of the signatures. Currently handles tags, LTTO beacons, LTAR beacons, and finds multibyte packets and gets the packet type from them.

===Planned features===

Finish decoding the multibyte packets, and check the checksums of them.

==ir_recoil==

The very beginnings of a decoder for Recoil laser tag IR signatures. Very much a work in progress, as I'm still figuring out how this protocol works. Was also my first Sigrok decoder, so I'll be coming back to it once I finish the others and cleaning it up. Currently gets the bit count and data from the signatures, but doesn't always decode them properly.

==ltar_smartdevice==

The start of a decoder for the LTAR laser tag blaster's Smart Device protocol. Currently broken.