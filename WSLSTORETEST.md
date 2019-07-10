# Plasma Store Performance Testing in WSL

# Numpy vs Pyarrow Store Capabilities
## Array ranging from 0 to 100000
### numpy array size: 800096 bytes
- `data = np.arange(100000, dtype="int64")`
### pyarrow tensor size: 800192 bytes
- 
### pyarrow array size: 80 bytes
- `arr = pa.array(data)`


# Storage duration as capacity decreases
- 

# Max Storage Capacity Before Eviction  (Trial 2)
- `data = np.arange(100000, dtype="int64")`

## Method 1: Reformat to pyarrow arrays
800192 bytes per obj

### 1 gig Store
- 0.333680064 gigabytes

### 10 gig Store
- 6.58317958 gigabytes


## Method 2: Limbo numpy arrays
800640 bytes per obj

### 1 gig Store
- 0.33386688 gigabytes

### 10 gig Store
- 6.58286208 gigabytes

<br>

# Max Storage Capacity Before Eviction  (Trial 1 [OLD])
- `data = np.arange(100000, dtype="int64")`

## Method 1: Reformat to pyarrow arrays
800000 bytes per obj

### 1 gig Store
- 1005 objs (0.804 gigs) (80.4%)

### 10 gig Store
- 10732 objs (8.5856 gigs) (85.856%)

### 100 gig Store
- 85887 objs (68.7096 gigs) (68.7096%)


## Method 2: Limbo numpy arrays
800640 bytes per obj

### 1 gig Store
- 667 objs (0.53402688 gigs) (53.402688%)

### 10 gig Store
- 8222 objs (6.58286208 gigs) (65.8286208%) 

### 100 gig Store
- 60833 objs (48.7053331 gigs) (48.7053331%)