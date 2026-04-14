import svgPaths from "./svg-yp9ddzalpq";
import imgTeacherProfileAvatar from "figma:asset/1f04c4cac1101c903f48b838e8e5d1aef1591811.png";

function Container1() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px overflow-clip relative" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal justify-center leading-[0] relative shrink-0 text-[#6b7280] text-[14px] w-full">
        <p className="leading-[normal]">Search lessons, materials, or students...</p>
      </div>
    </div>
  );
}

function Input() {
  return (
    <div className="bg-[#f2f3fd] relative rounded-[9999px] shrink-0 w-full" data-name="Input">
      <div className="flex flex-row justify-center overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex items-start justify-center pl-[40px] pr-[16px] py-[9px] relative w-full">
          <Container1 />
        </div>
      </div>
    </div>
  );
}

function Container() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Container">
      <Input />
      <div className="absolute bottom-1/4 left-[15px] top-1/4 w-[18px]" data-name="Icon">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 18">
          <path d={svgPaths.p8a35e00} fill="var(--fill-0, #414754)" id="Icon" />
        </svg>
      </div>
    </div>
  );
}

function Button() {
  return (
    <div className="h-[20px] relative shrink-0 w-[16px]" data-name="Button">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16 20">
        <g id="Button">
          <path d={svgPaths.p164b49c0} fill="var(--fill-0, #414754)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Button1() {
  return (
    <div className="relative shrink-0 size-[20px]" data-name="Button">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20 20">
        <g id="Button">
          <path d={svgPaths.p2816f2c0} fill="var(--fill-0, #414754)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container3() {
  return (
    <div className="content-stretch flex gap-[16px] items-center relative shrink-0" data-name="Container">
      <Button />
      <Button1 />
    </div>
  );
}

function Button2() {
  return (
    <div className="content-stretch flex flex-col items-center justify-center px-[16px] py-[8px] relative shrink-0" data-name="Button">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:SemiBold',sans-serif] font-semibold h-[20px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[14px] text-center w-[87.14px]">
        <p className="leading-[20px]">Quick Action</p>
      </div>
    </div>
  );
}

function Button3() {
  return (
    <div className="content-stretch flex flex-col items-center justify-center px-[24px] py-[8px] relative rounded-[9999px] shrink-0" data-name="Button" style={{ backgroundImage: "linear-gradient(165.342deg, rgb(0, 91, 191) 0%, rgb(26, 115, 232) 100%)" }}>
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[20px] justify-center leading-[0] relative shrink-0 text-[14px] text-center text-white w-[89.63px]">
        <p className="leading-[20px]">Start Session</p>
      </div>
    </div>
  );
}

function Container2() {
  return (
    <div className="content-stretch flex gap-[24px] items-center relative shrink-0" data-name="Container">
      <Container3 />
      <div className="bg-[rgba(193,198,214,0.3)] h-[24px] shrink-0 w-px" data-name="Vertical Divider" />
      <Button2 />
      <Button3 />
    </div>
  );
}

function Margin() {
  return (
    <div className="content-stretch flex flex-col items-start pl-[32px] relative shrink-0" data-name="Margin">
      <Container2 />
    </div>
  );
}

function HeaderTopNavBar() {
  return (
    <div className="bg-[#f9f9ff] h-[64px] relative shrink-0 w-full z-[2]" data-name="Header - TopNavBar">
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex items-center justify-between pl-[32px] pr-[48px] py-[16px] relative size-full">
          <Container />
          <Margin />
        </div>
      </div>
    </div>
  );
}

function Container6() {
  return (
    <div className="h-[10.5px] relative shrink-0 w-[12.833px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12.8333 10.5">
        <g id="Container">
          <path d={svgPaths.p27737a70} fill="var(--fill-0, #005BBF)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container5() {
  return (
    <div className="content-stretch flex gap-[8px] items-center relative shrink-0 w-full" data-name="Container">
      <Container6 />
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[20px] justify-center leading-[0] relative shrink-0 text-[#005bbf] text-[14px] tracking-[1.4px] uppercase w-[145.8px]">
        <p className="leading-[20px]">Mathematics 101</p>
      </div>
    </div>
  );
}

function Heading1() {
  return (
    <div className="content-stretch flex flex-col items-start pt-[4px] relative shrink-0 w-full" data-name="Heading 2">
      <div className="flex flex-col font-['Manrope:ExtraBold',sans-serif] font-extrabold h-[96px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[48px] w-[312.3px]">
        <p className="leading-[48px] mb-0">Unit 3: Linear</p>
        <p className="leading-[48px]">Equations</p>
      </div>
    </div>
  );
}

function Container7() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal h-[56px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[18px] w-[432.52px]">
        <p className="leading-[28px] mb-0">Exploring fundamental algebraic concepts through</p>
        <p className="leading-[28px]">graphical representation.</p>
      </div>
    </div>
  );
}

function Container4() {
  return (
    <div className="content-stretch flex flex-col gap-[4px] items-start relative shrink-0 w-[432.52px]" data-name="Container">
      <Container5 />
      <Heading1 />
      <Container7 />
    </div>
  );
}

function Container9() {
  return (
    <div className="relative shrink-0 size-[18px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 18">
        <g id="Container">
          <path d={svgPaths.pad10a80} fill="var(--fill-0, #191C23)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Button4() {
  return (
    <div className="bg-white content-stretch flex gap-[9.79px] items-center pl-[24px] pr-[25.8px] py-[12px] relative rounded-[9999px] shrink-0" data-name="Button">
      <Container9 />
      <div className="flex flex-col font-['Plus_Jakarta_Sans:SemiBold',sans-serif] font-semibold h-[48px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[16px] text-center w-[54.64px]">
        <p className="leading-[24px] mb-0">Edit</p>
        <p className="leading-[24px]">Lesson</p>
      </div>
    </div>
  );
}

function Container10() {
  return (
    <div className="h-[14px] relative shrink-0 w-[11px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 11 14">
        <g id="Container">
          <path d="M0 14V0L11 7L0 14V14" fill="var(--fill-0, white)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Button5() {
  return (
    <div className="content-stretch flex gap-[12.18px] items-center pl-[32px] pr-[36.19px] py-[12px] relative rounded-[9999px] shrink-0" data-name="Button" style={{ backgroundImage: "linear-gradient(154.642deg, rgb(0, 91, 191) 0%, rgb(26, 115, 232) 100%)" }}>
      <Container10 />
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[48px] justify-center leading-[0] relative shrink-0 text-[16px] text-center text-white w-[60.55px]">
        <p className="leading-[24px] mb-0">Start</p>
        <p className="leading-[24px]">Session</p>
      </div>
    </div>
  );
}

function Container11() {
  return (
    <div className="h-[12.025px] relative shrink-0 w-[21.9px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 21.9 12.025">
        <g id="Container">
          <path d={svgPaths.p1b15f878} fill="var(--fill-0, #006F67)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Button6() {
  return (
    <div className="bg-[#8bf1e6] content-stretch flex h-[48px] items-center justify-center relative rounded-[9999px] shrink-0 w-[36.03px]" data-name="Button">
      <Container11 />
    </div>
  );
}

function Container8() {
  return (
    <div className="content-stretch flex gap-[12px] items-center pb-[8px] relative shrink-0" data-name="Container">
      <Button4 />
      <Button5 />
      <Button6 />
    </div>
  );
}

function HeaderSectionWithAsymmetry() {
  return (
    <div className="content-stretch flex items-end justify-between relative shrink-0 w-full" data-name="Header Section with Asymmetry">
      <Container4 />
      <Container8 />
    </div>
  );
}

function Heading2() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Heading 3">
      <div className="flex flex-col font-['Manrope:Bold',sans-serif] font-bold h-[32px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[24px] w-[200px]">
        <p className="leading-[32px]">Current Progress</p>
      </div>
    </div>
  );
}

function Container14() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal h-[20px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[14px] w-[255px]">
        <p className="leading-[20px]">Last accessed 2 hours ago by Dr. Sarah</p>
      </div>
    </div>
  );
}

function Container13() {
  return (
    <div className="content-stretch flex flex-col gap-[4px] items-start relative shrink-0 w-[255px]" data-name="Container">
      <Heading2 />
      <Container14 />
    </div>
  );
}

function Background() {
  return (
    <div className="bg-[#8bf1e6] content-stretch flex flex-col items-start px-[16px] py-[6px] relative rounded-[9999px] shrink-0" data-name="Background">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[16px] justify-center leading-[0] relative shrink-0 text-[#006f67] text-[12px] w-[80.92px]">
        <p className="leading-[16px]">IN PROGRESS</p>
      </div>
    </div>
  );
}

function Container12() {
  return (
    <div className="relative shrink-0 w-full" data-name="Container">
      <div className="content-stretch flex items-start justify-between pr-[0.01px] relative w-full">
        <Container13 />
        <Background />
      </div>
    </div>
  );
}

function Svg() {
  return (
    <div className="relative size-[192px]" data-name="SVG">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 192 192">
        <g id="SVG">
          <path d={svgPaths.p3e462d48} id="Vector" stroke="var(--stroke-0, #E0E2EC)" strokeWidth="12" />
          <path d={svgPaths.p3e462d48} id="Vector_2" stroke="url(#paint0_linear_1_384)" strokeLinecap="round" strokeWidth="12" />
        </g>
        <defs>
          <linearGradient gradientUnits="userSpaceOnUse" id="paint0_linear_1_384" x1="8" x2="184" y1="8" y2="184">
            <stop stopColor="#006A63" />
            <stop offset="1" stopColor="#005BBF" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}

function Container16() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 size-[192px]" data-name="Container">
      <div className="flex items-center justify-center relative shrink-0 size-[192px]" style={{ "--transform-inner-width": "1185", "--transform-inner-height": "21" } as React.CSSProperties}>
        <div className="-rotate-90 flex-none">
          <Svg />
        </div>
      </div>
      <div className="absolute flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold inset-[68px_55.26px_84px_55.27px] justify-center leading-[0] text-[#191c23] text-[36px]">
        <p className="leading-[40px]">65%</p>
      </div>
      <div className="absolute flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold inset-[108px_58.39px_68px_58.39px] justify-center leading-[0] text-[#414754] text-[12px] tracking-[1.2px] uppercase">
        <p className="leading-[16px]">Complete</p>
      </div>
    </div>
  );
}

function Container19() {
  return (
    <div className="-translate-y-1/2 absolute h-[16px] left-0 top-1/2 w-[20px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20 16">
        <g id="Container">
          <path d={svgPaths.p1c9cc680} fill="var(--fill-0, #005BBF)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container20() {
  return (
    <div className="-translate-y-1/2 absolute content-stretch flex flex-col items-start left-[32.02px] top-1/2" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[16px] justify-center leading-[0] relative shrink-0 text-[#005bbf] text-[12px] tracking-[0.6px] uppercase w-[48.47px]">
        <p className="leading-[16px]">Topics</p>
      </div>
    </div>
  );
}

function Container18() {
  return (
    <div className="h-[24px] relative shrink-0 w-full" data-name="Container">
      <Container19 />
      <Container20 />
    </div>
  );
}

function Container22() {
  return (
    <div className="absolute bottom-0 h-[22.71px] left-0 w-[27.593px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 27.5925 22.71">
        <g id="Container">
          <path d={svgPaths.p2a21e880} fill="var(--fill-0, #191C23)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container23() {
  return (
    <div className="absolute bottom-0 content-stretch flex flex-col items-start left-[34px] pb-[4px]" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal h-[24px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[16px] w-[22.86px]">
        <p className="leading-[24px]">/18</p>
      </div>
    </div>
  );
}

function Container21() {
  return (
    <div className="h-[36px] relative shrink-0 w-full" data-name="Container">
      <Container22 />
      <Container23 />
    </div>
  );
}

function Background2() {
  return (
    <div className="bg-[#e0e2ec] h-[6px] overflow-clip relative rounded-[9999px] shrink-0 w-full" data-name="Background">
      <div className="absolute bg-[#005bbf] inset-[0_34.02%_0_0] rounded-[9999px]" data-name="Background" />
    </div>
  );
}

function Background1() {
  return (
    <div className="bg-[#ecedf7] col-1 justify-self-stretch relative rounded-[16px] row-1 self-start shrink-0" data-name="Background">
      <div className="content-stretch flex flex-col gap-[12px] items-start p-[24px] relative w-full">
        <Container18 />
        <Container21 />
        <Background2 />
      </div>
    </div>
  );
}

function Container25() {
  return (
    <div className="-translate-y-1/2 absolute left-0 size-[20px] top-1/2" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20 20">
        <g id="Container">
          <path d={svgPaths.p13915240} fill="var(--fill-0, #005BBF)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container26() {
  return (
    <div className="-translate-y-1/2 absolute content-stretch flex flex-col items-start left-[32.01px] top-1/2" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[16px] justify-center leading-[0] relative shrink-0 text-[#005bbf] text-[12px] tracking-[0.6px] uppercase w-[55.31px]">
        <p className="leading-[16px]">Quizzes</p>
      </div>
    </div>
  );
}

function Container24() {
  return (
    <div className="h-[24px] relative shrink-0 w-full" data-name="Container">
      <Container25 />
      <Container26 />
    </div>
  );
}

function Container28() {
  return (
    <div className="absolute bottom-0 content-stretch flex flex-col items-start left-0" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[36px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[30px] w-[19.63px]">
        <p className="leading-[36px]">4</p>
      </div>
    </div>
  );
}

function Container29() {
  return (
    <div className="absolute bottom-0 content-stretch flex flex-col items-start left-[23.62px] pb-[4px]" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal h-[24px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[16px] w-[16.73px]">
        <p className="leading-[24px]">/5</p>
      </div>
    </div>
  );
}

function Container27() {
  return (
    <div className="h-[36px] relative shrink-0 w-full" data-name="Container">
      <Container28 />
      <Container29 />
    </div>
  );
}

function Background4() {
  return (
    <div className="bg-[#e0e2ec] h-[6px] overflow-clip relative rounded-[9999px] shrink-0 w-full" data-name="Background">
      <div className="absolute bg-[#005bbf] inset-[0_20.02%_0_0] rounded-[9999px]" data-name="Background" />
    </div>
  );
}

function Background3() {
  return (
    <div className="bg-[#ecedf7] col-2 justify-self-stretch relative rounded-[16px] row-1 self-start shrink-0" data-name="Background">
      <div className="content-stretch flex flex-col gap-[12px] items-start p-[24px] relative w-full">
        <Container24 />
        <Container27 />
        <Background4 />
      </div>
    </div>
  );
}

function Container31() {
  return (
    <div className="-translate-y-1/2 absolute left-0 size-[20px] top-1/2" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20 20">
        <g id="Container">
          <path d={svgPaths.p643d217} fill="var(--fill-0, #005BBF)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container32() {
  return (
    <div className="-translate-y-1/2 absolute content-stretch flex flex-col items-start left-[32.01px] top-1/2" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[16px] justify-center leading-[0] relative shrink-0 text-[#005bbf] text-[12px] tracking-[0.6px] uppercase w-[71.81px]">
        <p className="leading-[16px]">Materials</p>
      </div>
    </div>
  );
}

function Container30() {
  return (
    <div className="h-[24px] relative shrink-0 w-full" data-name="Container">
      <Container31 />
      <Container32 />
    </div>
  );
}

function Container34() {
  return (
    <div className="absolute bottom-0 content-stretch flex flex-col items-start left-0" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[36px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[30px] w-[18.97px]">
        <p className="leading-[36px]">8</p>
      </div>
    </div>
  );
}

function Container35() {
  return (
    <div className="absolute bottom-0 content-stretch flex flex-col items-start left-[22.97px] pb-[4px]" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal h-[24px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[16px] w-[22.41px]">
        <p className="leading-[24px]">/12</p>
      </div>
    </div>
  );
}

function Container33() {
  return (
    <div className="h-[36px] relative shrink-0 w-full" data-name="Container">
      <Container34 />
      <Container35 />
    </div>
  );
}

function Background6() {
  return (
    <div className="bg-[#e0e2ec] h-[6px] overflow-clip relative rounded-[9999px] shrink-0 w-full" data-name="Background">
      <div className="absolute bg-[#005bbf] inset-[0_34.02%_0_0] rounded-[9999px]" data-name="Background" />
    </div>
  );
}

function Background5() {
  return (
    <div className="bg-[#ecedf7] col-3 justify-self-stretch relative rounded-[16px] row-1 self-start shrink-0" data-name="Background">
      <div className="content-stretch flex flex-col gap-[12px] items-start p-[24px] relative w-full">
        <Container30 />
        <Container33 />
        <Background6 />
      </div>
    </div>
  );
}

function Container17() {
  return (
    <div className="flex-[1_0_0] gap-x-[24px] gap-y-[24px] grid grid-cols-[repeat(3,minmax(0,1fr))] grid-rows-[_138px] h-[138px] min-h-px min-w-px relative" data-name="Container">
      <Background1 />
      <Background3 />
      <Background5 />
    </div>
  );
}

function Container15() {
  return (
    <div className="content-stretch flex gap-[48px] items-center pt-[8px] relative shrink-0 w-full" data-name="Container">
      <Container16 />
      <Container17 />
    </div>
  );
}

function Container37() {
  return (
    <div className="relative shrink-0 size-[20px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20 20">
        <g id="Container">
          <path d={svgPaths.p256e1340} fill="var(--fill-0, #414754)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container38() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:SemiBold',sans-serif] font-semibold h-[20px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[14px] w-[211.57px]">
        <p>
          <span className="leading-[20px]">{`Estimated Completion: `}</span>
          <span className="font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold leading-[20px] text-[#005bbf]">45 mins</span>
        </p>
      </div>
    </div>
  );
}

function Container36() {
  return (
    <div className="relative shrink-0" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[8px] items-center relative">
        <Container37 />
        <Container38 />
      </div>
    </div>
  );
}

function Container40() {
  return (
    <div className="h-[12px] relative shrink-0 w-[24px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 24 12">
        <g id="Container">
          <path d={svgPaths.p5df3d80} fill="var(--fill-0, #414754)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container41() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:SemiBold',sans-serif] font-semibold h-[20px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[14px] w-[157.02px]">
        <p>
          <span className="leading-[20px]">{`Attending: `}</span>
          <span className="font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold leading-[20px] text-[#005bbf]">24 Students</span>
        </p>
      </div>
    </div>
  );
}

function Container39() {
  return (
    <div className="relative shrink-0" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[8px] items-center relative">
        <Container40 />
        <Container41 />
      </div>
    </div>
  );
}

function HorizontalBorder() {
  return (
    <div className="content-stretch flex gap-[24px] items-center pt-[33px] relative shrink-0 w-full" data-name="HorizontalBorder">
      <div aria-hidden="true" className="absolute border-[rgba(193,198,214,0.15)] border-solid border-t inset-0 pointer-events-none" />
      <Container36 />
      <Container39 />
    </div>
  );
}

function ProgressStatsLargeCard() {
  return (
    <div className="bg-white col-[1/span_8] justify-self-stretch relative rounded-[24px] row-1 self-start shadow-[0px_20px_40px_0px_rgba(25,28,35,0.04)] shrink-0" data-name="Progress & Stats (Large Card)">
      <div className="content-stretch flex flex-col gap-[32px] items-start pb-[231px] pt-[32px] px-[32px] relative w-full">
        <Container12 />
        <Container15 />
        <HorizontalBorder />
      </div>
    </div>
  );
}

function Heading3() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0" data-name="Heading 3">
      <div className="flex flex-col font-['Manrope:Bold',sans-serif] font-bold h-[28px] justify-center leading-[0] relative shrink-0 text-[18px] text-white w-[164.52px]">
        <p className="leading-[28px]">Class Performance</p>
      </div>
    </div>
  );
}

function Button7() {
  return (
    <div className="h-[16px] relative shrink-0 w-[4px]" data-name="Button">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 4 16">
        <g id="Button">
          <path d={svgPaths.p3caf0c80} fill="var(--fill-0, white)" fillOpacity="0.5" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container43() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full" data-name="Container">
      <Heading3 />
      <Button7 />
    </div>
  );
}

function Container47() {
  return (
    <div className="h-[7px] relative shrink-0 w-[11.667px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 11.6667 7">
        <g id="Container">
          <path d={svgPaths.pde19380} fill="var(--fill-0, #8EF4E9)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container46() {
  return (
    <div className="absolute content-stretch flex items-center left-[117.2px] top-[26px]" data-name="Container">
      <Container47 />
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[20px] justify-center leading-[0] relative shrink-0 text-[#8ef4e9] text-[14px] w-[32.45px]">
        <p className="leading-[20px]">+3%</p>
      </div>
    </div>
  );
}

function Container45() {
  return (
    <div className="h-[48px] relative shrink-0 w-full" data-name="Container">
      <div className="-translate-y-1/2 absolute flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[48px] justify-center leading-[0] left-0 text-[48px] text-white top-[24px] w-[109.2px]">
        <p className="leading-[48px]">82%</p>
      </div>
      <Container46 />
    </div>
  );
}

function Container48() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal justify-center leading-[0] relative shrink-0 text-[14px] text-[rgba(255,255,255,0.6)] w-full">
        <p className="leading-[20px]">Average Score for Unit 3</p>
      </div>
    </div>
  );
}

function Container44() {
  return (
    <div className="content-stretch flex flex-col gap-[4px] items-start relative shrink-0 w-full" data-name="Container">
      <Container45 />
      <Container48 />
    </div>
  );
}

function Background8() {
  return (
    <div className="absolute bg-[#006a63] content-stretch flex flex-col items-start left-[-30.02%] px-[6px] py-[2px] right-[-29.97%] rounded-[4px] top-[-24px]" data-name="Background">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[15px] justify-center leading-[0] relative shrink-0 text-[10px] text-white w-[22.27px]">
        <p className="leading-[15px]">YOU</p>
      </div>
    </div>
  );
}

function Background7() {
  return (
    <div className="absolute bg-[#006a63] inset-[18%_82.23px_0_109.68px] rounded-tl-[2px] rounded-tr-[2px]" data-name="Background">
      <Background8 />
    </div>
  );
}

function MockLineGraph() {
  return (
    <div className="h-[96px] relative shrink-0 w-full" data-name="Mock Line Graph">
      <div className="absolute bg-[rgba(0,91,191,0.4)] inset-[60.01%_191.91px_0_0] rounded-tl-[2px] rounded-tr-[2px]" data-name="Overlay" />
      <div className="absolute bg-[rgba(0,91,191,0.4)] inset-[45%_164.49px_0_27.42px] rounded-tl-[2px] rounded-tr-[2px]" data-name="Overlay" />
      <div className="absolute bg-[rgba(0,91,191,0.4)] bottom-0 left-[54.84px] right-[137.07px] rounded-tl-[2px] rounded-tr-[2px] top-1/2" data-name="Overlay" />
      <div className="absolute bg-[rgba(0,91,191,0.4)] inset-[30.01%_109.65px_0_82.26px] rounded-tl-[2px] rounded-tr-[2px]" data-name="Overlay" />
      <div className="absolute bg-[rgba(0,91,191,0.4)] inset-[22.01%_54.8px_-0.01%_137.11px] rounded-tl-[2px] rounded-tr-[2px]" data-name="Overlay" />
      <div className="absolute bg-[rgba(0,91,191,0.4)] inset-[35.01%_27.38px_0_164.53px] rounded-tl-[2px] rounded-tr-[2px]" data-name="Overlay" />
      <div className="absolute bg-[rgba(0,91,191,0.4)] inset-[20%_-0.04px_0_191.95px] rounded-tl-[2px] rounded-tr-[2px]" data-name="Overlay" />
      <Background7 />
    </div>
  );
}

function Container49() {
  return (
    <div className="content-stretch flex flex-col items-center relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Italic',sans-serif] font-normal h-[32px] italic justify-center leading-[0] relative shrink-0 text-[12px] text-[rgba(255,255,255,0.6)] text-center w-[212.5px]">
        <p className="leading-[16px] mb-0">Class average is currently 3.2% higher</p>
        <p className="leading-[16px]">than grade standard.</p>
      </div>
    </div>
  );
}

function Container42() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-start relative shrink-0 w-full" data-name="Container">
      <Container43 />
      <Container44 />
      <MockLineGraph />
      <Container49 />
    </div>
  );
}

function BackgroundShadow() {
  return (
    <div className="relative rounded-[24px] shadow-[0px_20px_25px_-5px_rgba(0,0,0,0.1),0px_8px_10px_-6px_rgba(0,0,0,0.1)] shrink-0 w-full" data-name="Background+Shadow" style={{ backgroundImage: "linear-gradient(127.304deg, rgb(45, 48, 56) 0%, rgb(25, 28, 35) 100%)" }}>
      <div className="overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex flex-col items-start p-[32px] relative w-full">
          <div className="absolute bg-[rgba(0,91,191,0.2)] blur-[32px] right-[-39.99px] rounded-[9999px] size-[128px] top-[-40px]" data-name="Decorative element" />
          <Container42 />
        </div>
      </div>
    </div>
  );
}

function Heading4() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Heading 3">
      <div className="flex flex-col font-['Manrope:Bold',sans-serif] font-bold justify-center leading-[0] relative shrink-0 text-[#191c23] text-[16px] w-full">
        <p className="leading-[24px]">Quick Insights</p>
      </div>
    </div>
  );
}

function Container51() {
  return (
    <div className="h-[19px] relative shrink-0 w-[22px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 22 19">
        <g id="Container">
          <path d={svgPaths.p7555480} fill="var(--fill-0, #BA1A1A)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container53() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[16px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[12px] w-[126.58px]">
        <p className="leading-[16px]">4 Students Struggling</p>
      </div>
    </div>
  );
}

function Container54() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal h-[32px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[12px] w-[140.44px]">
        <p className="leading-[16px] mb-0">Recommended focus on</p>
        <p className="leading-[16px]">{`"Intercepts"`}</p>
      </div>
    </div>
  );
}

function Container52() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-[140.44px]" data-name="Container">
      <Container53 />
      <Container54 />
    </div>
  );
}

function Background9() {
  return (
    <div className="bg-[#f9f9ff] relative rounded-[12px] shrink-0 w-full" data-name="Background">
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex gap-[11.99px] items-center p-[12px] relative w-full">
          <Container51 />
          <Container52 />
        </div>
      </div>
    </div>
  );
}

function Container55() {
  return (
    <div className="h-[19px] relative shrink-0 w-[20px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20 19">
        <g id="Container">
          <path d={svgPaths.p1f93f980} fill="var(--fill-0, #006A63)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container57() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[16px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[12px] w-[128.56px]">
        <p className="leading-[16px]">Unit High-Score: 98%</p>
      </div>
    </div>
  );
}

function Container58() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal h-[32px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[12px] w-[157.67px]">
        <p className="leading-[16px] mb-0">Top performance by Marcus</p>
        <p className="leading-[16px]">V.</p>
      </div>
    </div>
  );
}

function Container56() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-[157.67px]" data-name="Container">
      <Container57 />
      <Container58 />
    </div>
  );
}

function Background10() {
  return (
    <div className="bg-[#f9f9ff] relative rounded-[12px] shrink-0 w-full" data-name="Background">
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex gap-[11.99px] items-center p-[12px] relative w-full">
          <Container55 />
          <Container56 />
        </div>
      </div>
    </div>
  );
}

function Container50() {
  return (
    <div className="content-stretch flex flex-col gap-[12px] items-start relative shrink-0 w-full" data-name="Container">
      <Background9 />
      <Background10 />
    </div>
  );
}

function ActionsCard() {
  return (
    <div className="bg-[#e0e2ec] relative rounded-[24px] shrink-0 w-full" data-name="Actions Card">
      <div className="content-stretch flex flex-col gap-[16px] items-start p-[24px] relative w-full">
        <Heading4 />
        <Container50 />
      </div>
    </div>
  );
}

function PerformanceAnalytics() {
  return (
    <div className="col-[9/span_4] content-stretch flex flex-col gap-[32px] items-start justify-self-stretch relative row-1 self-start shrink-0" data-name="Performance Analytics">
      <BackgroundShadow />
      <ActionsCard />
    </div>
  );
}

function Heading5() {
  return (
    <div className="content-stretch flex flex-col items-start pr-[103.81px] relative shrink-0" data-name="Heading 3">
      <div className="flex flex-col font-['Manrope:Bold',sans-serif] font-bold h-[64px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[24px] w-[125.33px]">
        <p className="leading-[32px] mb-0">Learning</p>
        <p className="leading-[32px]">Objectives</p>
      </div>
    </div>
  );
}

function Button8() {
  return (
    <div className="content-stretch flex flex-col items-center justify-center pl-[15.09px] pr-[15.11px] relative shrink-0" data-name="Button">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[40px] justify-center leading-[0] relative shrink-0 text-[#005bbf] text-[14px] text-center w-[31.32px]">
        <p className="leading-[20px] mb-0">Add</p>
        <p className="leading-[20px]">New</p>
      </div>
    </div>
  );
}

function Container59() {
  return (
    <div className="relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex items-center justify-between relative w-full">
          <Heading5 />
          <Button8 />
        </div>
      </div>
    </div>
  );
}

function Container60() {
  return (
    <div className="h-[7.015px] relative shrink-0 w-[9.508px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.50833 7.01458">
        <g id="Container">
          <path d={svgPaths.p25f8ca80} fill="var(--fill-0, white)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function BackgroundBorder() {
  return (
    <div className="bg-[#006a63] content-stretch flex items-center justify-center p-[2px] relative rounded-[9999px] shrink-0 size-[24px]" data-name="Background+Border">
      <div aria-hidden="true" className="absolute border-2 border-[#006a63] border-solid inset-0 pointer-events-none rounded-[9999px]" />
      <Container60 />
    </div>
  );
}

function Container62() {
  return (
    <div className="content-stretch flex flex-col items-start opacity-50 relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[48px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[16px] w-[233.83px]">
        <p className="[text-decoration-skip-ink:none] decoration-solid leading-[24px] line-through mb-0">Identify slope and y-intercept</p>
        <p className="[text-decoration-skip-ink:none] decoration-solid leading-[24px] line-through">from equations</p>
      </div>
    </div>
  );
}

function Container63() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal h-[16px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[12px] w-[133.72px]">
        <p className="leading-[16px]">Completed in Session 2</p>
      </div>
    </div>
  );
}

function Container61() {
  return (
    <div className="content-stretch flex flex-col gap-[4px] items-start relative self-stretch shrink-0 w-[233.83px]" data-name="Container">
      <Container62 />
      <Container63 />
    </div>
  );
}

function Item() {
  return (
    <div className="content-stretch flex gap-[16px] items-start relative shrink-0 w-full" data-name="Item">
      <BackgroundBorder />
      <Container61 />
    </div>
  );
}

function Container64() {
  return (
    <div className="h-[7.015px] relative shrink-0 w-[9.508px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.50833 7.01458">
        <g id="Container">
          <path d={svgPaths.p25f8ca80} fill="var(--fill-0, white)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function BackgroundBorder1() {
  return (
    <div className="bg-[#006a63] content-stretch flex items-center justify-center p-[2px] relative rounded-[9999px] shrink-0 size-[24px]" data-name="Background+Border">
      <div aria-hidden="true" className="absolute border-2 border-[#006a63] border-solid inset-0 pointer-events-none rounded-[9999px]" />
      <Container64 />
    </div>
  );
}

function Container66() {
  return (
    <div className="content-stretch flex flex-col items-start opacity-50 relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[48px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[16px] w-[233.55px]">
        <p className="[text-decoration-skip-ink:none] decoration-solid leading-[24px] line-through mb-0">Convert between point-slope</p>
        <p className="[text-decoration-skip-ink:none] decoration-solid leading-[24px] line-through">and standard form</p>
      </div>
    </div>
  );
}

function Container67() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal h-[16px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[12px] w-[133.72px]">
        <p className="leading-[16px]">Completed in Session 2</p>
      </div>
    </div>
  );
}

function Container65() {
  return (
    <div className="content-stretch flex flex-col gap-[4px] items-start relative self-stretch shrink-0 w-[233.55px]" data-name="Container">
      <Container66 />
      <Container67 />
    </div>
  );
}

function Item1() {
  return (
    <div className="content-stretch flex gap-[16px] items-start relative shrink-0 w-full" data-name="Item">
      <BackgroundBorder1 />
      <Container65 />
    </div>
  );
}

function Container69() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[48px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[16px] w-[219.16px]">
        <p className="leading-[24px] mb-0">Graph linear equations using</p>
        <p className="leading-[24px]">two coordinates</p>
      </div>
    </div>
  );
}

function Container70() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal h-[16px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[12px] w-[136.77px]">
        <p className="leading-[16px]">Scheduled for Session 3</p>
      </div>
    </div>
  );
}

function Container68() {
  return (
    <div className="content-stretch flex flex-col gap-[4px] items-start relative self-stretch shrink-0 w-[219.16px]" data-name="Container">
      <Container69 />
      <Container70 />
    </div>
  );
}

function Item2() {
  return (
    <div className="content-stretch flex gap-[16px] items-start relative shrink-0 w-full" data-name="Item">
      <div className="relative rounded-[9999px] shrink-0 size-[24px]" data-name="Border">
        <div aria-hidden="true" className="absolute border-2 border-[#c1c6d6] border-solid inset-0 pointer-events-none rounded-[9999px]" />
      </div>
      <Container68 />
    </div>
  );
}

function Container72() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[48px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[16px] w-[213.89px]">
        <p className="leading-[24px] mb-0">Apply linear models to real-</p>
        <p className="leading-[24px]">world scenarios</p>
      </div>
    </div>
  );
}

function Container73() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal h-[16px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[12px] w-[137.02px]">
        <p className="leading-[16px]">Scheduled for Session 4</p>
      </div>
    </div>
  );
}

function Container71() {
  return (
    <div className="content-stretch flex flex-col gap-[4px] items-start relative self-stretch shrink-0 w-[213.89px]" data-name="Container">
      <Container72 />
      <Container73 />
    </div>
  );
}

function Item3() {
  return (
    <div className="content-stretch flex gap-[16px] items-start relative shrink-0 w-full" data-name="Item">
      <div className="relative rounded-[9999px] shrink-0 size-[24px]" data-name="Border">
        <div aria-hidden="true" className="absolute border-2 border-[#c1c6d6] border-solid inset-0 pointer-events-none rounded-[9999px]" />
      </div>
      <Container71 />
    </div>
  );
}

function List() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-start relative shrink-0 w-full" data-name="List">
      <Item />
      <Item1 />
      <Item2 />
      <Item3 />
    </div>
  );
}

function LearningObjectives() {
  return (
    <div className="bg-white col-[1/span_5] justify-self-stretch relative rounded-[24px] row-2 self-start shadow-[0px_1px_2px_0px_rgba(0,0,0,0.05)] shrink-0" data-name="Learning Objectives">
      <div className="content-stretch flex flex-col gap-[32px] items-start p-[32px] relative w-full">
        <Container59 />
        <List />
      </div>
    </div>
  );
}

function Heading6() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0" data-name="Heading 3">
      <div className="flex flex-col font-['Manrope:Bold',sans-serif] font-bold h-[32px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[24px] w-[219.22px]">
        <p className="leading-[32px]">Teaching Materials</p>
      </div>
    </div>
  );
}

function Container75() {
  return (
    <div className="relative shrink-0 size-[9.333px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.33333 9.33333">
        <g id="Container">
          <path d={svgPaths.p19d05760} fill="var(--fill-0, #005BBF)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Button9() {
  return (
    <div className="content-stretch flex gap-[3.99px] items-center relative shrink-0" data-name="Button">
      <Container75 />
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[20px] justify-center leading-[0] relative shrink-0 text-[#005bbf] text-[14px] text-center w-[83.45px]">
        <p className="leading-[20px]">Upload New</p>
      </div>
    </div>
  );
}

function Container74() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full" data-name="Container">
      <Heading6 />
      <Button9 />
    </div>
  );
}

function Container78() {
  return (
    <div className="relative shrink-0 size-[25px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 25 25">
        <g id="Container">
          <path d={svgPaths.p17af4e40} fill="var(--fill-0, #006A63)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function BackgroundShadow1() {
  return (
    <div className="bg-[#8ef4e9] content-stretch flex h-[56px] items-center justify-center relative rounded-[8px] shadow-[0px_1px_2px_0px_rgba(0,0,0,0.05)] shrink-0 w-[48px]" data-name="Background+Shadow">
      <Container78 />
    </div>
  );
}

function Button10() {
  return (
    <div className="relative shrink-0 size-[18px]" data-name="Button">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 18">
        <g id="Button">
          <path d={svgPaths.p22fc1b80} fill="var(--fill-0, #414754)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container77() {
  return (
    <div className="content-stretch flex items-start justify-between relative shrink-0 w-full" data-name="Container">
      <BackgroundShadow1 />
      <Button10 />
    </div>
  );
}

function Margin1() {
  return (
    <div className="content-stretch flex flex-col items-start pb-[16px] relative shrink-0 w-full" data-name="Margin">
      <Container77 />
    </div>
  );
}

function Container80() {
  return (
    <div className="content-stretch flex flex-col items-start overflow-clip relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold justify-center leading-[0] relative shrink-0 text-[#191c23] text-[16px] w-full">
        <p className="leading-[24px]">Teacher_Guide_V1.…</p>
      </div>
    </div>
  );
}

function Background11() {
  return (
    <div className="bg-[#e0e2ec] content-stretch flex flex-col items-start px-[6px] py-[2px] relative rounded-[4px] shrink-0" data-name="Background">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[15px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[10px] w-[19.75px]">
        <p className="leading-[15px]">PDF</p>
      </div>
    </div>
  );
}

function Container82() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal h-[16px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[12px] w-[38.59px]">
        <p className="leading-[16px]">2.4 MB</p>
      </div>
    </div>
  );
}

function Container81() {
  return (
    <div className="content-stretch flex gap-[8px] items-center relative shrink-0 w-full" data-name="Container">
      <Background11 />
      <Container82 />
    </div>
  );
}

function Container79() {
  return (
    <div className="content-stretch flex flex-col gap-[4px] items-start relative shrink-0 w-full" data-name="Container">
      <Container80 />
      <Container81 />
    </div>
  );
}

function ResourceCard() {
  return (
    <div className="bg-[#ecedf7] col-1 justify-self-stretch relative rounded-[16px] row-1 self-start shrink-0" data-name="Resource Card 1">
      <div className="content-stretch flex flex-col items-start justify-between p-[20px] relative w-full">
        <Margin1 />
        <Container79 />
      </div>
    </div>
  );
}

function Container84() {
  return (
    <div className="relative shrink-0 size-[22.5px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 22.5 22.5">
        <g id="Container">
          <path d={svgPaths.p6f705b0} fill="var(--fill-0, #006A63)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function BackgroundShadow2() {
  return (
    <div className="bg-[#8ef4e9] content-stretch flex h-[56px] items-center justify-center relative rounded-[8px] shadow-[0px_1px_2px_0px_rgba(0,0,0,0.05)] shrink-0 w-[48px]" data-name="Background+Shadow">
      <Container84 />
    </div>
  );
}

function Button11() {
  return (
    <div className="relative shrink-0 size-[18px]" data-name="Button">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 18">
        <g id="Button">
          <path d={svgPaths.p22fc1b80} fill="var(--fill-0, #414754)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container83() {
  return (
    <div className="content-stretch flex items-start justify-between relative shrink-0 w-full" data-name="Container">
      <BackgroundShadow2 />
      <Button11 />
    </div>
  );
}

function Margin2() {
  return (
    <div className="content-stretch flex flex-col items-start pb-[16px] relative shrink-0 w-full" data-name="Margin">
      <Container83 />
    </div>
  );
}

function Container86() {
  return (
    <div className="content-stretch flex flex-col items-start overflow-clip relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold justify-center leading-[0] relative shrink-0 text-[#191c23] text-[16px] w-full">
        <p className="leading-[24px]">Visual_Aids_Linear_…</p>
      </div>
    </div>
  );
}

function Background12() {
  return (
    <div className="bg-[#e0e2ec] content-stretch flex flex-col items-start px-[6px] py-[2px] relative rounded-[4px] shrink-0" data-name="Background">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[15px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[10px] w-[19.75px]">
        <p className="leading-[15px]">PDF</p>
      </div>
    </div>
  );
}

function Container88() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal h-[16px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[12px] w-[35.44px]">
        <p className="leading-[16px]">5.1 MB</p>
      </div>
    </div>
  );
}

function Container87() {
  return (
    <div className="content-stretch flex gap-[8px] items-center relative shrink-0 w-full" data-name="Container">
      <Background12 />
      <Container88 />
    </div>
  );
}

function Container85() {
  return (
    <div className="content-stretch flex flex-col gap-[4px] items-start relative shrink-0 w-full" data-name="Container">
      <Container86 />
      <Container87 />
    </div>
  );
}

function ResourceCard1() {
  return (
    <div className="bg-[#ecedf7] col-2 justify-self-stretch relative rounded-[16px] row-1 self-start shrink-0" data-name="Resource Card 2">
      <div className="content-stretch flex flex-col items-start justify-between p-[20px] relative w-full">
        <Margin2 />
        <Container85 />
      </div>
    </div>
  );
}

function Container90() {
  return (
    <div className="h-[25px] relative shrink-0 w-[20px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20 25">
        <g id="Container">
          <path d={svgPaths.p1ec38700} fill="var(--fill-0, #006A63)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function BackgroundShadow3() {
  return (
    <div className="bg-[#8ef4e9] content-stretch flex h-[56px] items-center justify-center relative rounded-[8px] shadow-[0px_1px_2px_0px_rgba(0,0,0,0.05)] shrink-0 w-[48px]" data-name="Background+Shadow">
      <Container90 />
    </div>
  );
}

function Button12() {
  return (
    <div className="relative shrink-0 size-[18px]" data-name="Button">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 18">
        <g id="Button">
          <path d={svgPaths.p22fc1b80} fill="var(--fill-0, #414754)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container89() {
  return (
    <div className="content-stretch flex items-start justify-between relative shrink-0 w-full" data-name="Container">
      <BackgroundShadow3 />
      <Button12 />
    </div>
  );
}

function Margin3() {
  return (
    <div className="content-stretch flex flex-col items-start pb-[16px] relative shrink-0 w-full" data-name="Margin">
      <Container89 />
    </div>
  );
}

function Container92() {
  return (
    <div className="content-stretch flex flex-col items-start overflow-clip relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold justify-center leading-[0] relative shrink-0 text-[#191c23] text-[16px] w-full">
        <p className="leading-[24px]">Student_Worksheet…</p>
      </div>
    </div>
  );
}

function Background13() {
  return (
    <div className="bg-[#e0e2ec] content-stretch flex flex-col items-start px-[6px] py-[2px] relative rounded-[4px] shrink-0" data-name="Background">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[15px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[10px] w-[30.53px]">
        <p className="leading-[15px]">DOCX</p>
      </div>
    </div>
  );
}

function Container94() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal h-[16px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[12px] w-[42.09px]">
        <p className="leading-[16px]">840 KB</p>
      </div>
    </div>
  );
}

function Container93() {
  return (
    <div className="content-stretch flex gap-[8px] items-center relative shrink-0 w-full" data-name="Container">
      <Background13 />
      <Container94 />
    </div>
  );
}

function Container91() {
  return (
    <div className="content-stretch flex flex-col gap-[4px] items-start relative shrink-0 w-full" data-name="Container">
      <Container92 />
      <Container93 />
    </div>
  );
}

function ResourceCard2() {
  return (
    <div className="bg-[#ecedf7] col-1 justify-self-stretch relative rounded-[16px] row-2 self-start shrink-0" data-name="Resource Card 3">
      <div className="content-stretch flex flex-col items-start justify-between p-[20px] relative w-full">
        <Margin3 />
        <Container91 />
      </div>
    </div>
  );
}

function Container95() {
  return (
    <div className="relative shrink-0 size-[20px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20 20">
        <g id="Container">
          <path d={svgPaths.p2d8e4cc0} fill="var(--fill-0, #727785)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container96() {
  return (
    <div className="relative shrink-0" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col items-start relative">
        <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[20px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[14px] w-[113.42px]">
          <p className="leading-[20px]">Add more assets</p>
        </div>
      </div>
    </div>
  );
}

function AddButtonShell() {
  return (
    <div className="col-2 justify-self-stretch relative rounded-[16px] row-2 self-start shrink-0" data-name="Add Button Shell">
      <div aria-hidden="true" className="absolute border-2 border-[#c1c6d6] border-dashed inset-0 pointer-events-none rounded-[16px]" />
      <div className="flex flex-col items-center justify-center size-full">
        <div className="content-stretch flex flex-col gap-[8px] items-center justify-center px-[22px] py-[53.5px] relative w-full">
          <Container95 />
          <Container96 />
        </div>
      </div>
    </div>
  );
}

function Container76() {
  return (
    <div className="gap-x-[16px] gap-y-[16px] grid grid-cols-[repeat(2,minmax(0,1fr))] grid-rows-[__159px_159px] relative shrink-0 w-full" data-name="Container">
      <ResourceCard />
      <ResourceCard1 />
      <ResourceCard2 />
      <AddButtonShell />
    </div>
  );
}

function TeachingMaterials() {
  return (
    <div className="bg-white col-[6/span_7] justify-self-stretch relative rounded-[24px] row-2 self-start shadow-[0px_1px_2px_0px_rgba(0,0,0,0.05)] shrink-0" data-name="Teaching Materials">
      <div className="content-stretch flex flex-col gap-[32px] items-start pb-[74px] pt-[32px] px-[32px] relative w-full">
        <Container74 />
        <Container76 />
      </div>
    </div>
  );
}

function BentoGridLayout() {
  return (
    <div className="gap-x-[32px] gap-y-[32px] grid grid-cols-[repeat(12,minmax(0,1fr))] grid-rows-[__640px_504px] relative shrink-0 w-full" data-name="Bento Grid Layout">
      <ProgressStatsLargeCard />
      <PerformanceAnalytics />
      <LearningObjectives />
      <TeachingMaterials />
    </div>
  );
}

function MainPageContent() {
  return (
    <div className="bg-[#f2f3fd] relative shrink-0 w-full z-[1]" data-name="Main - Page Content">
      <div className="content-stretch flex flex-col gap-[32px] items-start pb-[128px] pt-[48px] px-[48px] relative w-full">
        <HeaderSectionWithAsymmetry />
        <BentoGridLayout />
      </div>
    </div>
  );
}

function MainWrapper() {
  return (
    <div className="min-h-[1616px] relative shrink-0 w-full" data-name="Main Wrapper">
      <div className="content-stretch flex flex-col isolate items-start min-h-[inherit] pl-[288px] relative w-full">
        <HeaderTopNavBar />
        <MainPageContent />
      </div>
    </div>
  );
}

function Heading() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Heading 1">
      <div className="flex flex-col font-['Manrope:Bold',sans-serif] font-bold justify-center leading-[0] relative shrink-0 text-[#191c23] text-[20px] w-full">
        <p className="leading-[28px]">The Academic Atelier</p>
      </div>
    </div>
  );
}

function Container98() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal justify-center leading-[0] relative shrink-0 text-[#414754] text-[12px] tracking-[0.6px] uppercase w-full">
        <p className="leading-[16px]">Curated Workspace</p>
      </div>
    </div>
  );
}

function Container97() {
  return (
    <div className="relative shrink-0 w-full" data-name="Container">
      <div className="content-stretch flex flex-col items-start px-[8px] relative w-full">
        <Heading />
        <Container98 />
      </div>
    </div>
  );
}

function Margin4() {
  return (
    <div className="content-stretch flex flex-col items-start pb-[40px] relative shrink-0 w-full" data-name="Margin">
      <Container97 />
    </div>
  );
}

function Container99() {
  return (
    <div className="relative shrink-0 size-[18px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 18">
        <g id="Container">
          <path d={svgPaths.p20793584} fill="var(--fill-0, #414754)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container100() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Medium',sans-serif] font-medium h-[24px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[16px] w-[85.08px]">
        <p className="leading-[24px]">Dashboard</p>
      </div>
    </div>
  );
}

function Link() {
  return (
    <div className="relative rounded-[8px] shrink-0 w-full" data-name="Link">
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex gap-[12px] items-center px-[16px] py-[12px] relative w-full">
          <Container99 />
          <Container100 />
        </div>
      </div>
    </div>
  );
}

function Container101() {
  return (
    <div className="h-[16px] relative shrink-0 w-[22px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 22 16">
        <g id="Container">
          <path d={svgPaths.p2b6c7500} fill="var(--fill-0, #1A73E8)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container102() {
  return (
    <div className="relative shrink-0" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col items-start relative">
        <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[24px] justify-center leading-[0] relative shrink-0 text-[#1a73e8] text-[16px] w-[89.59px]">
          <p className="leading-[24px]">My Lessons</p>
        </div>
      </div>
    </div>
  );
}

function Link1() {
  return (
    <div className="bg-[#ecedf7] relative rounded-[8px] shrink-0 w-full" data-name="Link">
      <div aria-hidden="true" className="absolute border-[#1a73e8] border-r-4 border-solid inset-0 pointer-events-none rounded-[8px]" />
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex gap-[12px] items-center pl-[16px] pr-[20px] py-[12px] relative w-full">
          <Container101 />
          <Container102 />
        </div>
      </div>
    </div>
  );
}

function Container103() {
  return (
    <div className="h-[20px] relative shrink-0 w-[18px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20">
        <g id="Container">
          <path d={svgPaths.p2a946800} fill="var(--fill-0, #414754)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container104() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Medium',sans-serif] font-medium h-[24px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[16px] w-[72.7px]">
        <p className="leading-[24px]">Schedule</p>
      </div>
    </div>
  );
}

function Link2() {
  return (
    <div className="relative rounded-[8px] shrink-0 w-full" data-name="Link">
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex gap-[12px] items-center px-[16px] py-[12px] relative w-full">
          <Container103 />
          <Container104 />
        </div>
      </div>
    </div>
  );
}

function Container105() {
  return (
    <div className="h-[16px] relative shrink-0 w-[21.5px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 21.5 16">
        <g id="Container">
          <path d={svgPaths.p34cd900} fill="var(--fill-0, #414754)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container106() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Medium',sans-serif] font-medium h-[24px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[16px] w-[124.28px]">
        <p className="leading-[24px]">Materials Library</p>
      </div>
    </div>
  );
}

function Link3() {
  return (
    <div className="relative rounded-[8px] shrink-0 w-full" data-name="Link">
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex gap-[12px] items-center px-[16px] py-[12px] relative w-full">
          <Container105 />
          <Container106 />
        </div>
      </div>
    </div>
  );
}

function Nav() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[8px] items-start min-h-px min-w-px relative w-full" data-name="Nav">
      <Link />
      <Link1 />
      <Link2 />
      <Link3 />
    </div>
  );
}

function Container107() {
  return (
    <div className="relative shrink-0 size-[8.167px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 8.16667 8.16667">
        <g id="Container">
          <path d={svgPaths.p10ad69c0} fill="var(--fill-0, white)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Button13() {
  return (
    <div className="relative rounded-[9999px] shrink-0 w-full" data-name="Button" style={{ backgroundImage: "linear-gradient(168.69deg, rgb(0, 91, 191) 0%, rgb(26, 115, 232) 100%)" }}>
      <div className="flex flex-row items-center justify-center size-full">
        <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[7.99px] items-center justify-center px-[16px] py-[12px] relative w-full">
          <Container107 />
          <div className="flex flex-col font-['Plus_Jakarta_Sans:SemiBold',sans-serif] font-semibold h-[24px] justify-center leading-[0] relative shrink-0 text-[16px] text-center text-white w-[148.73px]">
            <p className="leading-[24px]">Create New Lesson</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Container108() {
  return (
    <div className="h-[20px] relative shrink-0 w-[20.1px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20.1 20">
        <g id="Container">
          <path d={svgPaths.p3cdadd00} fill="var(--fill-0, #414754)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container109() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Medium',sans-serif] font-medium h-[24px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[16px] w-[64.63px]">
        <p className="leading-[24px]">Settings</p>
      </div>
    </div>
  );
}

function Link4() {
  return (
    <div className="relative rounded-[8px] shrink-0 w-full" data-name="Link">
      <div className="flex flex-row items-center size-full">
        <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[12px] items-center pb-[12px] pt-[20px] px-[16px] relative w-full">
          <Container108 />
          <Container109 />
        </div>
      </div>
    </div>
  );
}

function Container110() {
  return (
    <div className="relative shrink-0 size-[20px]" data-name="Container">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20 20">
        <g id="Container">
          <path d={svgPaths.p2816f2c0} fill="var(--fill-0, #414754)" id="Icon" />
        </g>
      </svg>
    </div>
  );
}

function Container111() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Medium',sans-serif] font-medium h-[24px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[16px] w-[102.36px]">
        <p className="leading-[24px]">Help Support</p>
      </div>
    </div>
  );
}

function Link5() {
  return (
    <div className="relative rounded-[8px] shrink-0 w-full" data-name="Link">
      <div className="flex flex-row items-center size-full">
        <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[12px] items-center px-[16px] py-[12px] relative w-full">
          <Container110 />
          <Container111 />
        </div>
      </div>
    </div>
  );
}

function TeacherProfileAvatar() {
  return (
    <div className="max-w-[240px] relative rounded-[9999px] shrink-0 size-[40px]" data-name="Teacher Profile Avatar">
      <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-[9999px]">
        <img alt="" className="absolute left-0 max-w-none size-full top-0" src={imgTeacherProfileAvatar} />
      </div>
    </div>
  );
}

function Container113() {
  return (
    <div className="content-stretch flex flex-col items-start overflow-clip relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Bold',sans-serif] font-bold h-[20px] justify-center leading-[0] relative shrink-0 text-[#191c23] text-[14px] w-[113.56px]">
        <p className="leading-[20px]">Dr. Sarah Jenkins</p>
      </div>
    </div>
  );
}

function Container114() {
  return (
    <div className="content-stretch flex flex-col items-start overflow-clip relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-col font-['Plus_Jakarta_Sans:Regular',sans-serif] font-normal h-[16px] justify-center leading-[0] relative shrink-0 text-[#414754] text-[12px] w-[82.92px]">
        <p className="leading-[16px]">Lead Educator</p>
      </div>
    </div>
  );
}

function Container112() {
  return (
    <div className="content-stretch flex flex-col items-start overflow-clip relative shrink-0 w-[113.56px]" data-name="Container">
      <Container113 />
      <Container114 />
    </div>
  );
}

function Background14() {
  return (
    <div className="bg-[#ecedf7] relative rounded-[12px] shrink-0 w-full" data-name="Background">
      <div className="flex flex-row items-center size-full">
        <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[12px] items-center p-[16px] relative w-full">
          <TeacherProfileAvatar />
          <Container112 />
        </div>
      </div>
    </div>
  );
}

function HorizontalBorder1() {
  return (
    <div className="content-stretch flex flex-col gap-[8px] items-start pt-[25px] relative shrink-0 w-full" data-name="HorizontalBorder">
      <div aria-hidden="true" className="absolute border-[rgba(193,198,214,0.15)] border-solid border-t inset-0 pointer-events-none" />
      <Button13 />
      <Link4 />
      <Link5 />
      <Background14 />
    </div>
  );
}

function AsideSideNavBar() {
  return (
    <div className="absolute bg-[#f9f9ff] content-stretch flex flex-col h-[1616px] items-start justify-between left-0 p-[24px] top-0 w-[288px]" data-name="Aside - SideNavBar">
      <Margin4 />
      <Nav />
      <HorizontalBorder1 />
    </div>
  );
}

export default function Body() {
  return (
    <div className="bg-[#f9f9ff] content-stretch flex flex-col items-start relative size-full" data-name="Body">
      <MainWrapper />
      <AsideSideNavBar />
    </div>
  );
}