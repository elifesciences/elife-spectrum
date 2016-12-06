function T = TracePath(xd,yd,xe,ye)
%% function used for rearrangement of cells

% This code is free to use for any purposes, provided any publications resulting from the use of this code reference the original code/author.
% Author:  Babak Momeni (bmomeni@gmail.com)
% Date:    11/2012
% The code is not guaranteed to be free of errors. Please notify the author of any bugs, and contribute any modifications or bug fixes back to the original author.

% Finds the shortest path to an empty space in a neighborhood around a cell
% In cellular automata codes (the diffusion model or the fitness model), the path is used for rearranging in-plane cells

xc = xd;
yc = yd;

di = sign(xe-xd);
dj = sign(ye-yd);

T = zeros(abs(xd-xe)+abs(yd-ye),2);

if di == 0,
    di = 1;
end
if dj == 0,
    dj = 1;
end
ss = [di 0; 0 dj; di dj];
cc = 0;
while (abs(xc-xe)+abs(yc-ye))>0.5,
    cc = cc+1;
    nn = [xc yc; xc yc; xc yc] + ss;
    
    d(1) = abs((ye-yd)*(nn(1,1)-xd) - (xe-xd)*(nn(1,2)-yd));
    d(2) = abs((ye-yd)*(nn(2,1)-xd) - (xe-xd)*(nn(2,2)-yd));
    d(3) = abs((ye-yd)*(nn(3,1)-xd) - (xe-xd)*(nn(3,2)-yd));
    [M I] = min(d);
    
    xc = nn(I,1);
    yc = nn(I,2);
    T(cc,1) = xc;
    T(cc,2) = yc;
end
T = T(1:cc,:);

return