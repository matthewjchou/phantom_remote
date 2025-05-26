# phantom_remote
If you own a Devialet Phantom II, you know that - while it sounds amazing for music, its connectivity for TV usage is... lacking.
This is a solution to the Phantom II lacking eARC HDMI support, allowing you to control your volume using your TV remote.

This is heavily inspired by https://github.com/cadesalaberry/devialet-ir - before stumbling upon this, I didn't even realize the Phantom II could be controlled with simple REST requests.

The reason I didn't just use that solution out of the gate was:
1. I ordered a different board (ESP32C3) than was used in that project (ESP32C6)
2. Because I thought it'd be fun

So instead of adapting the code to work with my board, I figured it'd be fun to tinker and get it to work myself.

I used micropython instead of writing C++, but otherwise, this is extremely similar. It still uses mDNS to discover the Phantom II, and it uses the same IR receiver to decode signals and turn them into REST requests to change the volume and mute the phantom. 

Couple quirks:
1. The ESP32C3 has no onboard LED, so there is no blinking if something is broken, unfortunate
2. The ESP32C3 has a very basic implementation of mDNS that allows for self advertisements, but does not implement Service Discovery. So the (mDNS library)[https://github.com/cbrand/micropython-mdns] I used uses the same port as the baked in mDNS implementation. That's a problem, so you can't use a prebuilt ESP32C3 firmware image, you have to build one yourself with mDNS disabled. There are more detailed instructions in that library READMEs
3. The ESP32C3 doesn't support sofware timers, so to use the (IR Receiver library)[https://github.com/peterhinch/micropython_ir] I used, you have to disable the software timer.

If you were to say use a different board, some things would need to be tweaked.

I also didn't bother supporting other remotes for now. So, right now, it only works with NEC 16 protocol remotes, which my TCL/Roku TV is.

