
### 

fname = "gdas.t18z.abias.txt"

with open(fname, "r") as f:
    lines = f.readlines()
i = 0
while i < len(lines):
    header = lines[i].split()
    record = int(header[0])
    sensor = header[1]
    channel = int(header[2])
    bias = float(header[3])
    nobs = float(header[4])
    npred = int(header[5])

    coeffs = (
        list(map(float, lines[i + 1].split())) +
        list(map(float, lines[i + 2].split()))
    )
    print(f"\nRecord {record}")
    print(f"  Sensor  : {sensor}")
    print(f"  Channel : {channel}")
    print(f"  Bias    : {bias}")
    print(f"  Nobs    : {nobs}")
    print(f"  Npred   : {npred}")
    print(f"  Coeffs  : {coeffs}")

    i += 3
