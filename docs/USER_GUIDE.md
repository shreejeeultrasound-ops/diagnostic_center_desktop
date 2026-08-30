# Diagnostic Center — User Guide

## Starting the application

Double-click the **Diagnostic Center** icon on your Desktop or Start Menu.
The Dashboard opens showing your center's name, today's patient count, and
today's collection.

## First-time setup

Before capturing patients, do these two things once (from the Dashboard,
click **Settings**):

1. **Company details** — enter your center's name, address, phone, and
   (optionally) a logo image. These appear on every DC and Customer
   Investigation Report you print.
2. **Add doctors and investigation types** — go to **Master Data** to add
   the doctors you work with and the investigations you offer (e.g. "USG
   Abdomen", with its usual fee).

## Recording a patient visit

1. Click **New Data Entry** (or the equivalent item in the left menu).
2. Fill in the patient's name (required), address, mobile, age, and
   father/husband's name.
3. Choose the **Doctor** and **Investigation Type** from the dropdowns —
   the fee fills in automatically from the investigation's usual price,
   but you can adjust it for this visit.
4. Enter a **Discount** if applicable. **Net Fees** updates automatically.
5. Click **SAVE**. You'll see a confirmation, and the form clears itself
   so you can start the next patient immediately.

To find and correct an existing entry, use **View / Search Entries** —
filter by today, a date range, patient name, or mobile number, then click
**Edit** on the row you need.

## Doctor-wise statement (DC)

1. Go to **DC Generation**.
2. Choose the doctor and a date range, then click **Generate / Preview**.
3. The list of patients for that doctor/period appears with totals at the
   bottom.
4. Click **Save as PDF** to save the file, or **Print** to open it in your
   PDF viewer and print from there.

## Customer Investigation Report

This is the document you hand to a patient — it does **not** contain any
clinical findings or diagnosis; it only confirms the patient's details and
which investigation and doctor the visit was for.

1. Go to **Customer Reports**.
2. Search by patient name, mobile, doctor, or investigation type.
3. Click **Preview** next to the correct visit to see a summary.
4. Click **Generate PDF** to save it, or **Print** to open and print it.

## Retiring a doctor or investigation type

You can never truly delete a doctor or investigation type once it has been
used, because that would break old DCs and reports. Instead, go to
**Master Data**, find the record, and click **Deactivate**. It will no
longer appear when creating a *new* entry, but every past entry that used
it keeps displaying correctly.

## Backing up your data

Go to **Settings → Backup Database** regularly (e.g. weekly, or before any
big change) and save the backup file somewhere safe — a USB drive or
cloud-synced folder. If you ever need to recover, use
**Settings → Restore Database** and select that saved file. You will be
asked to confirm before anything is replaced.

## If something goes wrong

You will see a plain-language message rather than a technical error. The
technical detail is saved automatically to a log file for support purposes
(patient names/addresses are never written to this log). If the
application will not start at all, your data is safe — it lives separately
from the application itself and is not affected by application updates.
