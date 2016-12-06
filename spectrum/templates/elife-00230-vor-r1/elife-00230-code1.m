%% Fitness Model
%% Cellular Automata model for growth of yeast communities

% This code is free to use for any purposes, provided any publications resulting from the use of this code reference the original code/author.
% Author:  Babak Momeni (bmomeni@gmail.com)
% Date:    11/2012
% The code is not guaranteed to be free of errors. Please notify the author of any bugs, and contribute any modifications or bug fixes back to the original author.

% space occupied by dead cells
% CI: confinement independent
% ES: Expansion to sides
% CD3: Occupancy modified next to surface and at top

clear
rndseed = 2734;
rand('twister',rndseed)

savename = 'CA3D_PP_CD3_ES_DB_c5_6N100_6N100_72r12_72r21_t300_rg2_ri3_Nc100Nz300';

%% Parameters
r1 = 0.05; % population 1 reproduction rate, per hour
r2 = 0.05; % population 2 reproduction rate, per hour

r12 = 0.6;
r21 = 0.6;

%% Definition of solution domain
% Length scale
c = 5; % grid size for cells, microns
ri = 3; % interaction radius, grids

rg0 = 2; % neghborhood radius for expansion to sides
chi = 0.8; % reduction fold caused by crowdedness

%% Cell simulation domain
Nc = 100; % cell domain size for cells
Nz = 300; % cell domain height for cells

%% Initial cell distrbution
CSD = 100; % initial cell surface density per type, 1/mm2
N1 = round(2*1/2*CSD*c*Nc*c*Nc/1e6); % initial number of type 1 cells, (R)
N2 = round(2*1/2*CSD*c*Nc*c*Nc/1e6); % initial number of type 2 cells, (Y)
X = zeros(Nc,Nc,Nz); % Cells
nn = 0;
while nn < N1,
    i = floor(Nc*rand(1))+1;
    j = floor(Nc*rand(1))+1;
    k = 1;
    if X(i,j,k) == 0;
        nn = nn+1;
        X(i,j,k) = 1;
    end
end
nn = 0;
while nn < N2,
    i = floor(Nc*rand(1))+1;
    j = floor(Nc*rand(1))+1;
    k = 1;
    if X(i,j,k) == 0;
        nn = nn+1;
        X(i,j,k) = 2;
    end
end

%% Cell-growth time-course
tau0 = 0; % in hours
tauf = 300; % in hours
dtau = 0.1; % in hours, cell growth update and uptake timescale
ts = 1; % in hours, sampling time for snapshots of sections

r1e = r1*dtau; % probability of reproduction in a time step
r2e = r2*dtau; % probability of reproduction in a time step
r12e = r12*dtau; % probability of reproduction in a time step
r21e = r21*dtau; % probability of reproduction in a time step

taurng = tau0:dtau:tauf;

X1lm = zeros(size(taurng));
X2lm = zeros(size(taurng));
X1m = zeros(size(taurng));
X2m = zeros(size(taurng));

ct = 0;
cS = 0;

Q = [1 0; -1 0; 0 1; 0 -1; 1 -1; -1 1; 1 1; -1 -1]; % locations of eight neighbor grids

for tau = taurng,
    ct = ct+1;
    tic

    % Update local abundances
    Xe = zeros(Nc+2*ri,Nc+2*ri,Nz+2*ri);
    Xe(ri+1:ri+Nc,ri+1:ri+Nc,ri+1:ri+Nz) = X;
    Xe(1:ri,ri+1:ri+Nc,ri+1:ri+Nz) = X(Nc-ri+1:Nc,1:Nc,1:Nz);
    Xe(Nc+ri+1:Nc+2*ri,ri+1:ri+Nc,ri+1:ri+Nz) = X(1:ri,1:Nc,1:Nz);
    Xe(ri+1:ri+Nc,1:ri,ri+1:ri+Nz) = X(1:Nc,Nc-ri+1:Nc,1:Nz);
    Xe(ri+1:ri+Nc,Nc+ri+1:Nc+2*ri,ri+1:ri+Nz) = X(1:Nc,1:ri,1:Nz);
    Xe(1:Nc+2*ri,1:Nc+2*ri,1:ri) = 0;
    Xe(1:Nc+2*ri,1:Nc+2*ri,Nz+ri+1:Nz+2*ri) = -1;
    
    Ac = zeros(Nc,Nc,Nz); % Physically occupied, not cells
    A1 = zeros(Nc,Nc,Nz); % Abundance of population #1
    A2 = zeros(Nc,Nc,Nz); % Abundance of population #2
    for ii = -ri:ri,
        for jj = -ri:ri,
            for kk = -ri:ri,
                Ac = Ac + (Xe(ii+ri+1:ii+ri+Nc,jj+ri+1:jj+ri+Nc,kk+ri+1:kk+ri+Nz)==-1);
                A1 = A1 + (Xe(ii+ri+1:ii+ri+Nc,jj+ri+1:jj+ri+Nc,kk+ri+1:kk+ri+Nz)==1);
                A2 = A2 + (Xe(ii+ri+1:ii+ri+Nc,jj+ri+1:jj+ri+Nc,kk+ri+1:kk+ri+Nz)==2);
            end
        end
    end

    A1 = A1./((2*ri+1)^3-Ac);
    A2 = A2./((2*ri+1)^3-Ac);

    % Update cell activity
    [zm,zi] = sort(rand(1,Nz-1)); % random order for cells at different heights
    for z = zi,
        [I,J] = find((X(:,:,z)==1)+(X(:,:,z)==2)); % find all live cells at height z
        Ncc = length(I);
        [SS,OS] = sort(rand(1,Ncc));
        I = I(OS);
        J = J(OS);
        for cc = 1:Ncc;

            xd = I(cc); % location of cell along x
            yd = J(cc); % location of cell along y

            r1l = (1-chi*(A1(xd,yd,z)+A2(xd,yd,z))) * (r1e + r12e*A2(xd,yd,z)*(1-A1(xd,yd,z)));
            r2l = (1-chi*(A1(xd,yd,z)+A2(xd,yd,z))) * (r2e + r21e*A1(xd,yd,z)*(1-A2(xd,yd,z)));
            
            live = 1;

            dividing = 0;
            % Is the cell dividing?
            cr = rand(1);
            if (X(xd,yd,z) == 1)&&(live==1)&&(cr < r1l),
                dividing = 1;
            end
            if (X(xd,yd,z) == 2)&&(live==1)&&(cr < r2l),
                dividing = 1;
            end

            % Cell division and rearrangement
            if (live==1)&&(dividing==1),
                Budded = 0;
                Natt = 0;
                [qm1,qi1] = sort(rand(1,4)); % random index for neighboring grids
                [qm2,qi2] = sort(rand(1,4)); % random index for neighboring grids
                qi = [qi1 4+qi2];
                while (Budded==0)&&(Natt<8), % try immediate neighboring grids
                    Natt = Natt+1;
                    xb = I(cc) + Q(qi(Natt),1);
                    if xb > Nc, xb = xb-Nc; end
                    if xb < 1, xb = xb+Nc; end
                    yb = J(cc) + Q(qi(Natt),2);
                    if yb > Nc, yb = yb-Nc; end
                    if yb < 1, yb = yb+Nc; end

                    if X(xb,yb,z)==0, % if available space, bud into it
                        zb = z;
                        while (zb>=2)&&(X(xb,yb,zb-1)==0),
                            zb = zb-1;
                        end
                        Budded = 1;
                        X(xb,yb,zb) = X(xd,yd,z);
                    end
                end
                if (Budded==0), % try extended neighborhood in the same plane
                    rg = rg0;
                    xdp = xd;
                    ydp = yd;
                    if xd+rg > Nc,
                        Xp = [X(:,:,z); X(1:xd+rg-Nc,:,z)];
                    else
                        if xd-rg < 1,
                            Xp = [X(Nc+xd-rg:Nc,:,z); X(:,:,z)];
                            xdp = rg+1;
                        else
                            Xp = X(:,:,z);
                        end
                    end
                    if yd+rg > Nc,
                        Xp = [Xp, Xp(:,1:yd+rg-Nc)];
                    else
                        if yd-rg < 1,
                            Xp = [Xp(:,Nc+yd-rg:Nc), Xp];
                            ydp = rg+1;
                        end
                    end
                    Ng = Xp(xdp-rg:xdp+rg,ydp-rg:ydp+rg);
                    if sum(sum(Ng>0.25))<(2*rg+1)^2,
                        [Ie,Je] = find(Ng==0);
                        [SSe,OSe] = min(sqrt((Ie-rg-1).^2+(Je-rg-1).^2));
                        if SSe <= rg,
                            xe = Ie(OSe);
                            ye = Je(OSe);
                            TP = TracePath(rg+1,rg+1,xe,ye);
                            NT = size(TP,1);
                            TP(:,1) = TP(:,1) + xd-rg-1;
                            TP(:,1) = TP(:,1) + Nc*((TP(:,1)<1)-(TP(:,1)>Nc));
                            TP(:,2) = TP(:,2) + yd-rg-1;
                            TP(:,2) = TP(:,2) + Nc*((TP(:,2)<1)-(TP(:,2)>Nc));
                            for ctr = NT-1:-1:2,
                                X(TP(ctr,1),TP(ctr,2),z) = X(TP(ctr-1,1),TP(ctr-1,2),z);
                            end
                            zb = z;
                            while (zb>=2)&&(X(TP(NT,1),TP(NT,2),zb-1)==0),
                                zb = zb-1;
                            end
                            X(TP(NT,1),TP(NT,2),zb) = X(TP(NT-1,1),TP(NT-1,2),z);
                            X(TP(1,1),TP(1,2),z) = X(xd,yd,z);
                            Budded = 1;
                        end
                    end
                end
                if (Budded == 0), % bud to top
                    X(xd,yd,z+1:Nz) = X(xd,yd,z:Nz-1);
                end
            end
        end
        X1lm(z,ct) = sum(sum(X(:,:,z)==1));
        X2lm(z,ct) = sum(sum(X(:,:,z)==2));
        X1m(z,ct) = sum(sum((X(:,:,z)>0.25).*(X(:,:,z)<1.25)));
        X2m(z,ct) = sum(sum((X(:,:,z)>1.25).*(X(:,:,z)<2.25)));
    end
    disp([tau  sum(X1lm(:,ct)) sum(X2lm(:,ct)) sum(sum(sum(X==0.5))) sum(sum(sum(X==1.5)))])

    if mod(tau+0.03,ts)<0.1,
        cS = cS+1;
        XS1(:,:,cS) = sum((X>0.25).*(X<1.25),3);
        XS2(:,:,cS) = sum((X>1.25).*(X<2.25),3);
        ss = round(Nc/2);
        for ii = 1:Nc,
            for jj = 1:Nz,
                Sec(ii,jj,cS) = X(ss,ii,jj);
            end
        end
        save(strcat(savename,'_ts1_cs',num2str(cS)),'X','tau')
    end
    toc
end

figure
semilogy(linspace(0,tau-dtau,ct-1),sum(X1lm(:,1:ct-1)),'r')
hold on
semilogy(linspace(0,tau-dtau,ct-1),sum(X2lm(:,1:ct-1)),'g')
xlabel('Time (hours)')
ylabel('Population (# of cells)')
xlim([0 tau-dtau])

figure
semilogy(sum(X1lm(:,1:ct-1))+sum(X2lm(:,1:ct-1)),sum(X1lm(:,1:ct-1))./sum(X2lm(:,1:ct-1)),'r')
xlabel('Total live population')
ylabel('Pop1:Pop2')

save(savename)
