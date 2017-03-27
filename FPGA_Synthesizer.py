import sys
from magma import *
from mantle import *
from boards.icestick import IceStick
import random
from scipy import signal
import numpy as np

icestick = IceStick()
icestick.Clock.on()
icestick.D1.on()
icestick.D2.on()
icestick.D3.on()
icestick.D4.on()
icestick.D5.on()

for i in range(4):
	icestick.PMOD0[i].output().on()

for i in range(4):
    icestick.PMOD1[i].input().on()


main = icestick.main()
frequency_length = 16


def Add(A, B):
    n = len(A)
    add = [FullAdder() for i in range(n)]

    CIN = 0
    O = []
    for i in range(n):
        wire(A[i], add[i].I0)
        wire(B[i], add[i].I1)
        wire(CIN, add[i].CIN)
        CIN = add[i].COUT
        O.append(add[i].O)
    return array(*O), CIN

def REGs(n):
    return [Register(16) for i in range(n)]

def MUXs(n):
    return [Mux(2,16) for i in range(n)]

def ROM(logn, init, A):
    n = 1 << logn
    assert len(A) == logn
    assert len(init) == n

    muxs = MUXs(n-1)
    for i in range(n/2):
        muxs[i](init[2*i], init[2*i+1], A[0])

    k = 0
    l = 1 << (logn-1)
    for i in range(logn-1):
        for j in range(l/2):
            muxs[k+l+j](muxs[k+2*j], muxs[k+2*j+1], A[i+1])
        k += l
        l /= 2

    return muxs[n-2]

# Converts a midi note to a frequency value.
# 69 will return 440, which is Middle A in tone
def MidiNoteValueToFrequency(MidiNote):
	exponent = (MidiNote - 69)/12
	return pow(2,exponent) * 440;

# Gets the value for a clock division comparator for a certain frequency
def GetClockDividerComparatorValueFromFreq(TargetFreq):
	MAX_CLOCK_HZ = 12000000;
	DivisionCompare = 12000000/TargetFreq;
	return array(*int2seq(DivisionCompare, 16))

# Returns a comparator value for clock division from a midi note.
def ComparaterValueFromMidiValue(MidiNote):
	return  GetClockDividerComparatorValueFromFreq(MidiNoteValueToFrequency(MidiNote))

# returns an wave table of a sin wave as an 'samples'x'bit_resolution' array
# samples       => number of samples for the wave table
# bit_reslution => bit resolution of sample values
def CreateSinWaveTable(samples, bit_resolution):
    wavetable = []
    HALF_PI = 3.14159/2
    for i in range(1<<LOGN):
        wavetable_sample = math.sin(HALF_PI * i/samples)
        wavetable.append(array(*int2seq(int(wavetable_sample), bit_resolution))) 


## returns a wave table as an 'samples'x'bit_resolution' array
# Uses scypi signal 
# samples       => number of samples for the wave table
# bit_reslution => bit resolution of sample values
def CreateSawtoothWaveTable(samples, bit_resolution):
     wavetable = []
     time_steps = np.linspace(0, 1, samples)
     for time_step in range(len(time_steps)):
        wavetable_sample = signal.sawtooth(2 * np.pi * 5 * time_step)
        wavetable.append(array(*int2seq(int(wavetable_sample), bit_resolution))) 

freq_1 = ComparaterValueFromMidiValue(69)




c = Counter(frequency_length)

# For demo, assigning button on PMOD pins to frequency and frequency modulation


LOGN = 5
bpm_clock_len = 21 
bpm_clock_enable = Counter(bpm_clock_len)
bpm_clock_inst = Counter(LOGN, ce=True, r = True)
negBPMButton = Xor2()(main.PMOD1[3],1)
bpm_clock = bpm_clock_inst(CE=bpm_clock_enable.COUT, RESET = negBPMButton)


LFO_CLOCK_BITNUM = 16
LFO_BAUD_LEN = 14
LFO_BAUD = Counter(LFO_BAUD_LEN)
LFOCounterDef =  Counter(LOGN , ce=True, r=True);
negLFOButton = Xor2()(main.PMOD1[2],1)
LFO_CLOCK = LFOCounterDef(CE=LFO_BAUD.COUT, RESET=negLFOButton)

init = []
for i in range(1<<LOGN):
    midi_note  =  30 + random.randint(0,18) * 7
    init.append( array(*int2seq(int(MidiNoteValueToFrequency(midi_note)), 16)) )


OSC_1_ROM = ROM(LOGN, init, bpm_clock)


init2 = []
for i in range(1<<LOGN):
    midi_note  =  random.randint(0,50) * 5
    init2.append( array(*int2seq(int(MidiNoteValueToFrequency(midi_note)), 16)) )


LFO_1_ROM = ROM(LOGN, init2, LFO_CLOCK)


sum, cout = Add(OSC_1_ROM.O, LFO_1_ROM.O,)
# comparator
ugtDef = UGE(frequency_length);
ugt_inst = ugtDef(sum, c.O)



# wire(bpm_clock_enable.O[bpm_clock_len - 1], main.D5)
wire(ugt_inst, main.PMOD0[0])
wire(ugt_inst, main.PMOD0[1])
wire(ugt_inst, main.PMOD0[2])
wire(ugt_inst, main.PMOD0[3])

wire(main.PMOD1[3], main.D1)
wire(LFO_CLOCK[0], main.D2)
# wire(main.PMOD1[0], main.D2)
wire(main.PMOD1[1], main.D3)
wire(main.PMOD1[2], main.D4)


compile(sys.argv[1], main)
# Clock is 12MHz