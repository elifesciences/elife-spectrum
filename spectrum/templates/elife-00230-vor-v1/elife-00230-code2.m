%% Diffusion model
%% Cellular Automata model for growth of yeast communities

% This code is free to use for any purposes, provided any publications resulting from the use of this code reference the original code/author.
% Author:  Babak Momeni (bmomeni@gmail.com)
% Date:    11/2012
% The code is not guaranteed to be free of errors. Please notify the author of any bugs, and contribute any modifications or bug fixes back to the original author.

% 3D diffusion for transfer of nutrients
% nonhomogeneous media
% space occupied by dead cells
% continuous uptake
% CI: Confinement by other cells does not directly affect the growth rate of cells
% ES: cells expand to the sides when there are empty spaces within a confinement neighborhood in the same plane
% PBC: periodic boundary condition
% LRA: live lys-requiring cells release adenine

clear
rndseed = 5489;
rand('twister',rndseed)

%% Parameters
SSF = 5e-4; % spatial scaling factor; grid size in cm
r1 = 0.395; % 937 reproduction rate, per hour
r2 = 0.35; % 1246 reproduction rate, per hour
d1 = 0.054; % death rate, per hour
d2 = 0.01; % death rate, per hour
alphaA = 1; % reproduction nutrient consumption factor; fmole per cell
alphaL = 2; % reproduction nutrient consumption factor; fmole per cell
gammaA = 0.08; % ade release rate; fmole per cell per hour
betaL = 15; % death nutrient release factor; fmole per cell
KA = 1e5; % Monod constant; fmole/ml
KL = 1e6; % Monod constant; fmole/ml

T1 = log(2)/r1; % minimum division time
T2 = log(2)/r2; % minimum division time
vmL = alphaL/T1; % maximum uptake rate, fmole/hour
vmA = alphaA/T2; % maximum uptake rate, fmole/hour

KmmL = KL; % Michaelis-Menten constant
KmmA = KA; % Michaelis-Menten constant

D0 = 360; % diffusion constant in agarose/agar, microns2/s
D1 = 360; % diffusion constant in cells, microns2/s

%% Definition of solution domain
%% Cell simulation domain
Nc = 150;
Nz = 60;
nc = round(Nc/2);
% [xx,yy,zz] = meshgrid(1:Nc,1:Nc,1:Nz);

%% Diffusion simulation domain
SC = 10; % ratio of diffusion grid to cell grid
Nd = 15; % domain size
Nsh = round(0.5*(Nd - floor(Nc/SC)));
Ns = 480; % thickness of agarose substrate
Ndz = floor(Ns+Nz/SC); % height
nd = round(Nd/2);
ndz = round(Ndz/2);

SA = zeros(Nd,Nd,Ndz);
SL = zeros(Nd,Nd,Ndz);
SAde = zeros(Nc,Nc,Nz);
SLde = zeros(Nc,Nc,Nz);

De = zeros(Nd+2,Nd+2,Ndz+2);

D = zeros(Nd,Nd,Ndz);
D(:,:,1:Ns) = D0;

% Length scale
g = 5; % grid size for cells, microns
d = g*SC; % grid size for diffusion, microns
dVc = g^3 * 1e-12; % volume of each grid cube for cells, ml
dV = d^3 * 1e-12; % volume of each grid cube for diffusion, ml

rg0 = 5; % neghborhood radius for expansion to sides

%% Initial cell distrbution
CSD = 250; % initial cell surface density per type, 1/mm2
Nc1 = round(CSD*g*Nc*g*Nc/1e6); % initial number of type 1 cells, (R)
Nc2 = round(CSD*g*Nc*g*Nc/1e6); % initial number of type 2 cells, (Y)
X = zeros(Nc,Nc,Nz); % Cells
U = zeros(Nc,Nc,Nz); % Nutrients taken up by cells
NB = zeros(Nc,Nc,Nz); % Number of budding events at each location
nn = 0;
while nn < Nc1,
    i = floor(Nc*rand(1))+1;
    j = floor(Nc*rand(1))+1;
    k = 1;
    if X(i,j,k) == 0;
        nn = nn+1;
        X(i,j,k) = 1;
        U(i,j,k) = rand(1)*alphaL; %to account for the asynchronous nature of cells - how much nutrient accumulated up to t=0
    end
end
nn = 0;
while nn < Nc2,
    i = floor(Nc*rand(1))+1;
    j = floor(Nc*rand(1))+1;
    k = 1;
    if X(i,j,k) == 0;
        nn = nn+1;
        X(i,j,k) = 2;
        U(i,j,k) = rand(1)*alphaA; %to account for the asynchronous nature of cells - how much nutrient accumulated up to t=0
    end
end

%% Cell-growth time-course
tau0 = 0; % in hours
tauf = 600; % in hours
dtau = 0.1; % in hours
ts = 2;

r1e = r1*dtau; % probability of reproduction in a time step
d1e = d1*dtau; % probability of death in a time step
r2e = r2*dtau; % probability of reproduction in a time step
d2e = d2*dtau; % probability of death in a time step

taurng = tau0:dtau:tauf;
tu = 0.1*KmmL*dV/vmL; % uptake update time-scale
ctu = 0; % counter for uptake timing

X1lm = zeros(size(taurng)); % number of live cells of type 1
X2lm = zeros(size(taurng)); % number of live cells of type 1
X1m = zeros(size(taurng)); % number of live cells of type 1
X2m = zeros(size(taurng)); % number of live cells of type 1
UAcc1 = zeros(size(taurng)); % Accumulated nutrients in live cells
UAcc2 = zeros(size(taurng)); % Accumulated nutrients in live cells
UW1 = zeros(size(taurng)); % Wasted nutrients in dead cells
UW2 = zeros(size(taurng)); % Wasted nutrients in dead cells
SLAccA = zeros(size(taurng)); % Total nutrients in the agar region
SLAccC = zeros(size(taurng)); % Total nutrients in the cell region
SAAccA = zeros(size(taurng)); % Total nutrients in the agar region
SAAccC = zeros(size(taurng)); % Total nutrients in the cell region

ct = 0;
cS = 0;

Q = [1 0; -1 0; 0 1; 0 -1; 1 -1; -1 1; 1 1; -1 -1]; % locations of eight neighbor grids

for tau = taurng,
    ct = ct+1;
    tic
    %     figure(1)
    %     imagesc(sum((X(:,:,1)>0.25).*(X(:,:,1)<1.25),3))
    %     axis image
    %     colormap([0 0 0; 0.1 0 0; 0.2 0 0; 0.3 0 0; 0.4 0 0; 0.5 0 0; 0.6 0 0; 0.7 0 0; 0.8 0 0; 0.9 0 0; 1 0 0])
    %
    %     figure(2)
    %     imagesc(sum((X(:,:,1)>1.25).*(X(:,:,1)<2.25),3))
    %     axis image
    %     colormap([0 0 0; 0 0.1 0; 0 0.2 0; 0 0.3 0; 0 0.4 0; 0 0.5 0; 0 0.6 0; 0 0.7 0; 0 0.8 0; 0 0.9 0; 0 1 0])

    for z = 1:Nz-1,
        zd = floor((z-1)/SC)+Ns+1;
        [I,J] = find((X(:,:,z)==1)+(X(:,:,z)==2));
        Ncc = length(I);
        [SS,OS] = sort(rand(1,Ncc));
        I = I(OS);
        J = J(OS);
        for cc = 1:Ncc;

            Id = floor((I(cc)-1)/SC)+Nsh+1;
            Jd = floor((J(cc)-1)/SC)+Nsh+1;
            xd = I(cc); % location of cell along x
            yd = J(cc); % location of cell along y

            live = 1;
            % Is the cell dead?
            cd = rand(1);
            if (X(xd,yd,z) == 1)&&(cd < d1e)&&(sum(sum(sum(X==1)))>1),
                X(xd,yd,z) = 0.5;
                live = 0;
            end
            if (X(xd,yd,z) == 2)&&(cd < d2e)&&(sum(sum(sum(X==2)))>1),
                X(xd,yd,z) = 1.5;
                SL(Id,Jd,zd) = SL(Id,Jd,zd)+betaL/dV;
                live = 0;
            end

            % Cell division and rearrangement
            if (X(xd,yd,z) == 1),
                alpha = alphaL;
            end
            if (X(xd,yd,z) == 2),
                alpha = alphaA;
            end

            if (live==1)&&(U(xd,yd,z) >= alpha),
                Budded = 0;
                Natt = 0;
                U(xd,yd,z) = U(xd,yd,z)-alpha;
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
                        NB(xd,yd,z) = NB(xd,yd,z)+1;
                        U(xb,yb,zb) = 0;
                    end
                end
                if (Budded==0), % try extended neighborhood in the same plane
                    rg = rg0;
                    xdp = xd;
                    ydp = yd;
                    if xd+rg > Nc,
                        Xp = [X(:,:,z); X(1:xd+rg-Nc,:,z)];  % extend along +x; size(Xp)=xd+rg
                    else
                        if xd-rg < 1,
                            Xp = [X(Nc+xd-rg:Nc,:,z); X(:,:,z)]; % extend along -x; size(Xp)=Nc-xd+rg+1
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
                            zb = z;
                            while (zb>=2)&&(X(TP(NT,1),TP(NT,2),zb-1)==0),
                                zb = zb-1;
                            end
                            X(TP(NT,1),TP(NT,2),zb) = X(TP(NT-1,1),TP(NT-1,2),z);
                            U(TP(NT,1),TP(NT,2),zb) = U(TP(NT-1,1),TP(NT-1,2),z);
                            for ctr = NT-1:-1:2,
                                X(TP(ctr,1),TP(ctr,2),z) = X(TP(ctr-1,1),TP(ctr-1,2),z);
                                U(TP(ctr,1),TP(ctr,2),z) = U(TP(ctr-1,1),TP(ctr-1,2),z);
                            end
                            X(TP(1,1),TP(1,2),z) = X(xd,yd,z);
                            U(TP(1,1),TP(1,2),z) = 0;
                            Budded = 1;
                        end
                    end
                end
                if (Budded == 0), % bud to top
                    X(xd,yd,z+1:Nz) = X(xd,yd,z:Nz-1);
                    U(xd,yd,z+2:Nz) = U(xd,yd,z+1:Nz-1);
                    U(xd,yd,z+1) = 0;
                end
            end

        end

        X1lm(z,ct) = sum(sum(X(:,:,z)==1));
        X2lm(z,ct) = sum(sum(X(:,:,z)==2));
        X1m(z,ct) = sum(sum((X(:,:,z)>0.25).*(X(:,:,z)<1.25)));
        X2m(z,ct) = sum(sum((X(:,:,z)>1.25).*(X(:,:,z)<2.25)));
    end
    UAcc1(ct) = sum(sum(sum(U.*(X==1))));
    UAcc2(ct) = sum(sum(sum(U.*(X==2))));
    UW1(ct) = sum(sum(sum(U.*(X==0.5))));
    UW2(ct) = sum(sum(sum(U.*(X==1.5))));
    SLAccC(ct) = sum(sum(sum(SL(:,:,Ns+1:Ndz))));
    SLAccA(ct) = sum(sum(sum(SL(:,:,1:Ns))));
    SAAccC(ct) = sum(sum(sum(SA(:,:,Ns+1:Ndz))));
    SAAccA(ct) = sum(sum(sum(SA(:,:,1:Ns))));
    disp([tau  sum(X1lm(:,ct)) sum(X2lm(:,ct)) sum(sum(sum(X==0.5))) sum(sum(sum(X==1.5))) sum(sum(sum(U.*(X==1)))) sum(sum(sum(U.*(X==2)))) 1e-6*mean(mean(mean(SL))) 1e-6*mean(mean(mean(SA)))])

    %% Diffusion loop
    % Update diffusion constant
    D(:,:,Ns+1:Ndz) = zeros(Nd,Nd,Ndz-Ns);
    for i1 = 1:SC,
        for i2 = 1:SC,
            for i3 = 1:SC,
                D(:,:,Ns+1:Ndz) = D(:,:,Ns+1:Ndz) + D1/SC^3*(X(i1:SC:Nc,i2:SC:Nc,i3:SC:Nz)>0.1);
            end
        end
    end
    De(2:Nd+1,2:Nd+1,2:Ndz+1) = D(1:Nd,1:Nd,1:Ndz);
    De(1,2:Nd+1,2:Ndz+1) = D(Nd,1:Nd,1:Ndz);
    De(Nd+2,2:Nd+1,2:Ndz+1) = D(1,1:Nd,1:Ndz);
    De(2:Nd+1,1,2:Ndz+1) = D(1:Nd,Nd,1:Ndz);
    De(2:Nd+1,Nd+2,2:Ndz+1) = D(1:Nd,1,1:Ndz);
    De(2:Nd+1,2:Nd+1,1) = D(1:Nd,1:Nd,1);
    De(2:Nd+1,2:Nd+1,Ndz+2) = D(1:Nd,1:Nd,Ndz);

    t0 = 0; % in seconds
    dt = 0.15*d^2/D0; % in seconds
    tf = dtau*3600; % in seconds
    trng = t0:dt:tf; % in seconds

    for t = trng,

        SLe(2:Nd+1,2:Nd+1,2:Ndz+1) = SL(1:Nd,1:Nd,1:Ndz);
        SLe(1,2:Nd+1,2:Ndz+1) = SL(Nd,1:Nd,1:Ndz);
        SLe(Nd+2,2:Nd+1,2:Ndz+1) = SL(1,1:Nd,1:Ndz);
        SLe(2:Nd+1,1,2:Ndz+1) = SL(1:Nd,Nd,1:Ndz);
        SLe(2:Nd+1,Nd+2,2:Ndz+1) = SL(1:Nd,1,1:Ndz);
        SLe(2:Nd+1,2:Nd+1,1) = SL(1:Nd,1:Nd,1);
        SLe(2:Nd+1,2:Nd+1,Ndz+2) = SL(1:Nd,1:Nd,Ndz);

        dSL = dt/d^2 * De(2:Nd+1,2:Nd+1,2:Ndz+1).*(SLe(1:Nd,2:Nd+1,2:Ndz+1) + SLe(3:Nd+2,2:Nd+1,2:Ndz+1) + SLe(2:Nd+1,1:Nd,2:Ndz+1) + SLe(2:Nd+1,3:Nd+2,2:Ndz+1) + SLe(2:Nd+1,2:Nd+1,1:Ndz) + SLe(2:Nd+1,2:Nd+1,3:Ndz+2) - 6*SLe(2:Nd+1,2:Nd+1,2:Ndz+1)) + dt/d^2 * ((De(3:Nd+2,2:Nd+1,2:Ndz+1)-De(2:Nd+1,2:Nd+1,2:Ndz+1)).*(SLe(3:Nd+2,2:Nd+1,2:Ndz+1)-SLe(2:Nd+1,2:Nd+1,2:Ndz+1)) + (De(2:Nd+1,3:Nd+2,2:Ndz+1)-De(2:Nd+1,2:Nd+1,2:Ndz+1)).*(SLe(2:Nd+1,3:Nd+2,2:Ndz+1)-SLe(2:Nd+1,2:Nd+1,2:Ndz+1)) + (De(2:Nd+1,2:Nd+1,3:Ndz+2)-De(2:Nd+1,2:Nd+1,2:Ndz+1)).*(SLe(2:Nd+1,2:Nd+1,3:Ndz+2)-SLe(2:Nd+1,2:Nd+1,2:Ndz+1)));
        SL = SL + dSL;

        SAe(2:Nd+1,2:Nd+1,2:Ndz+1) = SA(1:Nd,1:Nd,1:Ndz);
        SAe(1,2:Nd+1,2:Ndz+1) = SA(Nd,1:Nd,1:Ndz);
        SAe(Nd+2,2:Nd+1,2:Ndz+1) = SA(1,1:Nd,1:Ndz);
        SAe(2:Nd+1,1,2:Ndz+1) = SA(1:Nd,Nd,1:Ndz);
        SAe(2:Nd+1,Nd+2,2:Ndz+1) = SA(1:Nd,1,1:Ndz);
        SAe(2:Nd+1,2:Nd+1,1) = SA(1:Nd,1:Nd,1);
        SAe(2:Nd+1,2:Nd+1,Ndz+2) = SA(1:Nd,1:Nd,Ndz);

        dSA = dt/d^2 * De(2:Nd+1,2:Nd+1,2:Ndz+1).*(SAe(1:Nd,2:Nd+1,2:Ndz+1) + SAe(3:Nd+2,2:Nd+1,2:Ndz+1) + SAe(2:Nd+1,1:Nd,2:Ndz+1) + SAe(2:Nd+1,3:Nd+2,2:Ndz+1) + SAe(2:Nd+1,2:Nd+1,1:Ndz) + SAe(2:Nd+1,2:Nd+1,3:Ndz+2) - 6*SAe(2:Nd+1,2:Nd+1,2:Ndz+1)) + dt/d^2 * ((De(3:Nd+2,2:Nd+1,2:Ndz+1)-De(2:Nd+1,2:Nd+1,2:Ndz+1)).*(SAe(3:Nd+2,2:Nd+1,2:Ndz+1)-SAe(2:Nd+1,2:Nd+1,2:Ndz+1)) + (De(2:Nd+1,3:Nd+2,2:Ndz+1)-De(2:Nd+1,2:Nd+1,2:Ndz+1)).*(SAe(2:Nd+1,3:Nd+2,2:Ndz+1)-SAe(2:Nd+1,2:Nd+1,2:Ndz+1)) + (De(2:Nd+1,2:Nd+1,3:Ndz+2)-De(2:Nd+1,2:Nd+1,2:Ndz+1)).*(SAe(2:Nd+1,2:Nd+1,3:Ndz+2)-SAe(2:Nd+1,2:Nd+1,2:Ndz+1)));
        SA = SA + dSA;

        %% Uptake
        dtu = dt/3600; % in hours
        for i1 = 1:SC,
            for i2 = 1:SC,
                for i3 = 1:SC,
                    SLde(i1:SC:Nc,i2:SC:Nc,i3:SC:Nz) = SL(:,:,Ns+1:Ndz);
                    SAde(i1:SC:Nc,i2:SC:Nc,i3:SC:Nz) = SA(:,:,Ns+1:Ndz) + 1/dVc*gammaA*dtu*(X(i1:SC:Nc,i2:SC:Nc,i3:SC:Nz)==1);
                end
            end
        end
        UcL = (X==1).* min(dVc*SLde,(dtu*vmL*SLde./(SLde+KmmL)).*(SLde>0));
        UcA = (X==2).* min(dVc*SAde,(dtu*vmA*SAde./(SAde+KmmA)).*(SAde>0));
        U = U+UcL+UcA;
        SLde = SLde-1/dVc*UcL;
        SAde = SAde-1/dVc*UcA;
        SL(:,:,Ns+1:Ndz) = zeros(Nd,Nd,floor(Nz/SC));
        SA(:,:,Ns+1:Ndz) = zeros(Nd,Nd,floor(Nz/SC));
        for ii = 1:SC,
            for jj = 1:SC,
                for kk = 1:SC,
                    SL(:,:,Ns+1:Ndz) = SL(:,:,Ns+1:Ndz) + 1/SC^3*SLde(ii:SC:Nc,jj:SC:Nc,kk:SC:Nz);
                    SA(:,:,Ns+1:Ndz) = SA(:,:,Ns+1:Ndz) + 1/SC^3*SAde(ii:SC:Nc,jj:SC:Nc,kk:SC:Nz);
                end
            end
        end

    end
    if mod(tau+0.03,ts)<0.1,
        cS = cS+1;
        XS1(:,:,cS) = sum((X>0.25).*(X<1.25),3);
        XS2(:,:,cS) = sum((X>1.25).*(X<2.25),3);
        ss = 20;
        for ii = 1:Nc,
            for jj = 1:Nz,
                Sec(ii,jj,cS) = X(ss,ii,jj);
            end
        end
        save(strcat('CA3DCOOP_FCU_CI_ES_PBC_LRA_SC10_395N250_35N250_t600_rg5_N150Nz60Nd150Ns4800_tu1s_ts2_cs',num2str(cS)),'X','tau')

    end
    toc
    %     ss = 20;
    %     SecT = shiftdim(X(ss,:,:));
    %     figure(31); imagesc((SecT')); axis image
    %     colormap([0 0 0; 0.1 0 0; 0.2 0 0; 0.3 0 0; 0.4 0 0; 0.5 0 0; 0.6 0 0; 0.7 0 0; 0.8 0 0; 0.9 0 0; 1 0 0; 0 0.1 0; 0 0.2 0; 0 0.3 0; 0 0.4 0; 0 0.5 0; 0 0.6 0; 0 0.7 0; 0 0.8 0; 0 0.9 0; 0 1 0])

end

figure
semilogy(linspace(0,tau-dtau,ct-1),sum(X1lm(:,1:ct-1)),'r')
hold on
semilogy(linspace(0,tau-dtau,ct-1),sum(X1m(:,1:ct-1)),'r--')
semilogy(linspace(0,tau-dtau,ct-1),sum(X2lm(:,1:ct-1)),'g')
semilogy(linspace(0,tau-dtau,ct-1),sum(X2m(:,1:ct-1)),'g--')
xlabel('Time (hours)')
ylabel('Population (# of cells)')
xlim([0 tau-dtau])
legend('Live R','Total R','Live Y','Total Y')

figure
semilogy(linspace(0,tau-dtau,ct-1),sum(X2lm(:,1:ct-1))./sum(X1lm(:,1:ct-1)),'m')
xlabel('Time (hours)')
ylabel('Population ratio (G:R)')
xlim([0 tau-dtau])

save CA3DCOOP_FCU_CI_ES_PBC_LRA_SC10_395N250_35N250_t600_rg5_N150Nz60Nd150Ns4800_tu1s.mat