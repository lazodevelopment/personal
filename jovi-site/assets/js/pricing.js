/* Jovi Health membership pricing.
 * Mirrors the quote logic in the Jovi app's Onboarding widget (_computeQuote,
 * _computePetQuote). Keep the two in sync: if the app changes, change this.
 *
 *   basePremium(age): <=29 $150 · 30–39 $200 · 40–49 $250 · 50–59 $300 · 60+ $350
 *   tobacco: +15% on the primary member's base premium only
 *   dental: +$35 per person · vision: +$15 per person
 *   deductible(age): <=26 $1,500 · 27–45 $2,000 · 46–60 $2,500 · 61+ $3,000
 *   pets: $60/mo at 8–11 months; from 1 year, $60 + $7 per year of age (max 20);
 *         $500 deductible, 90% reimbursement
 *   plan type: Family when a spouse or any dependent is on the plan
 *   Jovi Pass: $49 one-time per priority visit (not part of the monthly total)
 */
(function (global) {
  'use strict';

  var JOVI_PASS_PRICE = 49;
  var DENTAL = 35;
  var VISION = 15;
  var TOBACCO_MULT = 1.15;
  var PET_DEDUCTIBLE = 500;
  var PET_REIMBURSEMENT = 90;

  function basePremium(age) {
    if (age <= 29) return 150;
    if (age <= 39) return 200;
    if (age <= 49) return 250;
    if (age <= 59) return 300;
    return 350;
  }

  function deductible(age) {
    if (age <= 26) return 1500;
    if (age <= 45) return 2000;
    if (age <= 60) return 2500;
    return 3000;
  }

  function petPremium(ageMonths) {
    if (ageMonths >= 8 && ageMonths <= 11) return 60;
    var years = Math.floor(ageMonths / 12);
    if (years >= 1 && years <= 20) return 60 + (years - 1) * 7;
    return 60;
  }

  /**
   * @param {Object} q
   * @param {number} q.primaryAge
   * @param {boolean} [q.tobacco]
   * @param {number|null} [q.spouseAge]
   * @param {number[]} [q.dependentAges]
   * @param {number[]} [q.petAgesMonths]
   * @param {boolean} [q.dental]
   * @param {boolean} [q.vision]
   */
  function quote(q) {
    var members = [];
    var people = [{ label: 'You', age: q.primaryAge, primary: true }];
    if (q.spouseAge != null) people.push({ label: 'Spouse', age: q.spouseAge, primary: false });
    (q.dependentAges || []).forEach(function (a, i) {
      people.push({ label: 'Dependent ' + (i + 1), age: a, primary: false });
    });

    var total = 0;
    people.forEach(function (p) {
      var base = basePremium(p.age);
      var premium = base;
      if (p.primary && q.tobacco) premium *= TOBACCO_MULT;
      if (q.dental) premium += DENTAL;
      if (q.vision) premium += VISION;
      premium = Math.round(premium * 100) / 100;
      total += premium;
      members.push({
        label: p.label,
        age: p.age,
        basePremium: base,
        premium: premium,
        deductible: deductible(p.age),
        tobacco: !!(p.primary && q.tobacco),
      });
    });

    var pets = [];
    var petTotal = 0;
    (q.petAgesMonths || []).forEach(function (m, i) {
      var prem = petPremium(m);
      petTotal += prem;
      pets.push({ label: 'Pet ' + (i + 1), ageMonths: m, premium: prem, deductible: PET_DEDUCTIBLE, reimbursement: PET_REIMBURSEMENT });
    });

    return {
      planType: (q.spouseAge != null || (q.dependentAges || []).length > 0) ? 'Family' : 'Individual',
      members: members,
      pets: pets,
      membersTotal: Math.round(total * 100) / 100,
      petsTotal: petTotal,
      grandTotal: Math.round((total + petTotal) * 100) / 100,
      primaryDeductible: members[0] ? members[0].deductible : deductible(q.primaryAge),
      joviPassPrice: JOVI_PASS_PRICE,
    };
  }

  function money(n) {
    var whole = Math.abs(n) % 1 === 0;
    return '$' + n.toLocaleString('en-US', { minimumFractionDigits: whole ? 0 : 2, maximumFractionDigits: 2 });
  }

  global.JoviPricing = {
    quote: quote,
    basePremium: basePremium,
    deductible: deductible,
    petPremium: petPremium,
    money: money,
    JOVI_PASS_PRICE: JOVI_PASS_PRICE,
    DENTAL: DENTAL,
    VISION: VISION,
  };

  // ── Calculator UI (present on pages that include the quote markup) ──
  function initCalculator(root) {
    var $ = function (id) { return root.querySelector('#' + id); };
    if (!$('qTotal')) return;

    var state = { primaryAge: 30, tobacco: false, spouse: false, spouseAge: 30, deps: [], pets: [], dental: false, vision: false };

    function slider(input, valueEl, onChange) {
      function paint() {
        var min = +input.min, max = +input.max, v = +input.value;
        input.style.setProperty('--p', ((v - min) / (max - min) * 100) + '%');
        if (valueEl) valueEl.textContent = v;
      }
      input.addEventListener('input', function () { paint(); onChange(+input.value); });
      paint();
    }

    function toggle(el, onChange) {
      function flip() {
        var on = el.getAttribute('aria-checked') !== 'true';
        el.setAttribute('aria-checked', on ? 'true' : 'false');
        onChange(on);
      }
      el.addEventListener('click', flip);
      el.addEventListener('keydown', function (e) { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); flip(); } });
    }

    function ageRow(label, min, max, value, unitLabel, onChange) {
      var row = document.createElement('div');
      row.className = 'q-row';
      row.innerHTML = '<div class="q-label">' + label + '</div><div class="q-slider"><input type="range" min="' + min + '" max="' + max + '" value="' + value + '" aria-label="' + label + '"><span class="q-val"></span></div>';
      var input = row.querySelector('input');
      var val = row.querySelector('.q-val');
      slider(input, null, function (v) { val.textContent = unitLabel(v); onChange(v); });
      val.textContent = unitLabel(value);
      return row;
    }

    function renderDeps() {
      var box = $('depAges');
      box.innerHTML = '';
      state.deps.forEach(function (age, i) {
        box.appendChild(ageRow('Dependent ' + (i + 1) + ' age', 0, 25, age, function (v) { return v; }, function (v) { state.deps[i] = v; recalc(); }));
      });
      box.classList.toggle('hidden', state.deps.length === 0);
      $('depV').textContent = state.deps.length;
    }

    function renderPets() {
      var box = $('petAges');
      box.innerHTML = '';
      state.pets.forEach(function (years, i) {
        box.appendChild(ageRow('Pet ' + (i + 1) + ' age', 1, 20, years, function (v) { return v + (v === 1 ? ' yr' : ' yrs'); }, function (v) { state.pets[i] = v; recalc(); }));
      });
      box.classList.toggle('hidden', state.pets.length === 0);
      $('petV').textContent = state.pets.length;
    }

    function recalc() {
      var r = quote({
        primaryAge: state.primaryAge,
        tobacco: state.tobacco,
        spouseAge: state.spouse ? state.spouseAge : null,
        dependentAges: state.deps,
        petAgesMonths: state.pets.map(function (y) { return y * 12; }),
        dental: state.dental,
        vision: state.vision,
      });
      $('qTotal').textContent = r.grandTotal.toLocaleString('en-US', { maximumFractionDigits: 2 });
      var lines = '<div class="q-line"><span>Members (' + r.members.length + ')</span><b>' + money(r.membersTotal) + '</b></div>';
      r.members.forEach(function (m) {
        var note = [];
        if (m.tobacco) note.push('tobacco');
        if (state.dental) note.push('dental');
        if (state.vision) note.push('vision');
        lines += '<div class="q-line sub"><span>' + m.label + ' · age ' + m.age + (note.length ? ' · ' + note.join(', ') : '') + '</span><b>' + money(m.premium) + '</b></div>';
      });
      if (r.pets.length) {
        lines += '<div class="q-line"><span>Pets (' + r.pets.length + ')</span><b>' + money(r.petsTotal) + '</b></div>';
        r.pets.forEach(function (p) {
          lines += '<div class="q-line sub"><span>' + p.label + ' · ' + (p.ageMonths / 12) + ' yr' + (p.ageMonths / 12 === 1 ? '' : 's') + '</span><b>' + money(p.premium) + '</b></div>';
        });
      }
      $('qBreak').innerHTML = lines;
      var deds = r.members.map(function (m) { return m.deductible; });
      var minD = Math.min.apply(null, deds), maxD = Math.max.apply(null, deds);
      $('qDed').textContent = minD === maxD ? money(minD) : money(minD) + ' – ' + money(maxD) + ' per person';
      $('qPlan').textContent = r.planType + ' plan';
      $('qPetTag').classList.toggle('hidden', r.pets.length === 0);
      var pass = $('qPass');
      if (pass) pass.textContent = 'Jovi Pass · ' + money(r.joviPassPrice) + ' per priority visit';
    }

    slider($('primaryAge'), $('primaryAgeV'), function (v) { state.primaryAge = v; recalc(); });
    slider($('spouseAge'), $('spouseAgeV'), function (v) { state.spouseAge = v; recalc(); });
    toggle($('tgTobacco'), function (on) { state.tobacco = on; recalc(); });
    toggle($('tgSpouse'), function (on) { state.spouse = on; $('spouseAgeRow').classList.toggle('hidden', !on); recalc(); });
    toggle($('tgDental'), function (on) { state.dental = on; recalc(); });
    toggle($('tgVision'), function (on) { state.vision = on; recalc(); });

    root.querySelectorAll('.stepper').forEach(function (st) {
      var kind = st.getAttribute('data-stepper');
      st.querySelectorAll('button').forEach(function (b) {
        b.addEventListener('click', function () {
          var d = +b.getAttribute('data-d');
          var arr = kind === 'dep' ? state.deps : state.pets;
          if (d > 0 && arr.length < 8) arr.push(kind === 'dep' ? 10 : 3);
          if (d < 0 && arr.length) arr.pop();
          if (kind === 'dep') renderDeps(); else renderPets();
          recalc();
        });
      });
    });

    renderDeps();
    renderPets();
    recalc();
  }

  if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function () { initCalculator(document); });
  }
})(typeof window !== 'undefined' ? window : this);
