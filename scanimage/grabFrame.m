function grabFrame(src,event,arguments)
    hSI = src.hSI; % get the handle to the ScanImage model
    lastStripe = hSI.hDisplay.stripeDataBuffer{hSI.hDisplay.stripeDataBufferPointer}; % get the pointer to the last acquired stripeData
    global frame;
    frame = lastStripe.roiData{1}.imageData{1}{1}; % extract all channels
    
    global mm;
    global header;
    
    mm.Data.data(:, :) = frame(:, :);
    mm.Data.data(1) = (now - 719529) * 86400 + 14400;
    header.Data(1) = 1;
end